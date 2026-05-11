from collections import OrderedDict

from psycopg2.extras import RealDictCursor

from app.core.countries import country_name_to_iso3
from app.db.connection import get_connection


def _resolve_presence_status(present_count: int, total_websites: int) -> str:
    if total_websites <= 0 or present_count <= 0:
        return "none"
    if present_count >= total_websites:
        return "all_present"
    return "partial"


def _resolve_family_status(format_rows: list[dict]) -> str:
    if not format_rows:
        return "none"

    statuses = {row["presence_status"] for row in format_rows}
    if statuses == {"all_present"}:
        return "all_present"
    if statuses == {"none"}:
        return "none"
    return "partial"


def _build_country_retailers(rows: list[dict]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    dedupe_by_country: dict[str, set[str]] = {}

    for row in rows:
        country = str(row.get("country") or "").strip()
        site_name = str(row.get("site_name") or "").strip()
        if not country or not site_name:
            continue

        grouped.setdefault(country, [])
        dedupe_by_country.setdefault(country, set())

        key = site_name.lower()
        if key in dedupe_by_country[country]:
            continue

        dedupe_by_country[country].add(key)
        grouped[country].append(site_name)

    for retailers in grouped.values():
        retailers.sort(key=lambda name: name.lower())

    return grouped


def _build_empty_response(
    selected_country: str | None,
    available_countries: list[str],
    country_retailers: dict[str, list[str]],
    rows: list[dict],
) -> dict:
    return {
        "country": selected_country,
        "available_countries": available_countries,
        "country_retailers": country_retailers,
        "websites": [],
        "kpis": {
            "total_product_families": len(rows),
            "total_formats": sum(len(row["formats"]) for row in rows),
            "total_websites": 0,
            "total_active_links": 0,
            "total_matrix_cells": 0,
            "present_cells": 0,
            "missing_cells": 0,
            "coverage_rate": 0.0,
        },
        "rows": rows,
    }


def get_retail_presence(country: str | None = None) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT country
                FROM websites
                WHERE country IS NOT NULL AND BTRIM(country) <> ''
                ORDER BY country
                """
            )
            available_countries = [str(row["country"]) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT country, site_name
                FROM websites
                WHERE country IS NOT NULL AND BTRIM(country) <> ''
                ORDER BY country, site_name
                """
            )
            country_retailers = _build_country_retailers(cur.fetchall())

            selected_country: str | None
            if country:
                selected_country = country.strip()
                if available_countries and selected_country not in available_countries:
                    raise ValueError(f"Unknown country '{selected_country}'")
            else:
                selected_country = None

            cur.execute(
                """
                SELECT
                    p.id AS product_id,
                    b.brand_name,
                    c.category_name,
                    r.range_name,
                    pv.id AS product_format_id,
                    f.format_name AS format,
                    pk.packaging_name AS packaging
                FROM products p
                JOIN brands b ON p.brand_id = b.id
                JOIN categories c ON p.category_id = c.id
                JOIN ranges r ON p.range_id = r.id
                JOIN product_variants pv ON pv.product_id = p.id
                JOIN formats f ON pv.format_id = f.id
                JOIN packagings pk ON pv.packaging_id = pk.id
                ORDER BY b.brand_name, c.category_name, r.range_name, f.format_name, pk.packaging_name
                """
            )
            format_base_rows = cur.fetchall()

            product_rows_map: OrderedDict[int, dict] = OrderedDict()
            for row in format_base_rows:
                product_id = int(row["product_id"])
                family_label = f"{row['brand_name']} {row['category_name']} {row['range_name']}"
                if product_id not in product_rows_map:
                    product_rows_map[product_id] = {
                        "product_id": product_id,
                        "family_label": family_label,
                        "presence_status": "none",
                        "present_formats": 0,
                        "total_formats": 0,
                        "formats": [],
                    }

            product_rows = list(product_rows_map.values())

            if not available_countries:
                return _build_empty_response(selected_country, available_countries, country_retailers, product_rows)

            if selected_country:
                cur.execute(
                    """
                    SELECT id AS website_id, site_name, country
                    FROM websites
                    WHERE country = %s
                    ORDER BY site_name
                    """,
                    (selected_country,),
                )
            else:
                cur.execute(
                    """
                    SELECT id AS website_id, site_name, country
                    FROM websites
                    ORDER BY country NULLS LAST, site_name
                    """
                )
            websites = cur.fetchall()
            website_ids = [int(row["website_id"]) for row in websites]

            if not website_ids:
                return _build_empty_response(selected_country, available_countries, country_retailers, product_rows)

            website_ids_tuple = tuple(website_ids)

            cur.execute(
                """
                SELECT DISTINCT pu.product_variant_id AS product_format_id, pu.website_id
                FROM product_urls pu
                WHERE pu.is_active = TRUE
                  AND pu.website_id IN %s
                """,
                (website_ids_tuple,),
            )
            presence_pairs = {
                (int(row["product_format_id"]), int(row["website_id"])) for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT COUNT(*)::int AS total
                FROM product_urls pu
                WHERE pu.is_active = TRUE
                  AND pu.website_id IN %s
                """,
                (website_ids_tuple,),
            )
            total_active_links = int((cur.fetchone() or {}).get("total", 0) or 0)

    website_count = len(website_ids)

    for row in format_base_rows:
        product_id = int(row["product_id"])
        product_format_id = int(row["product_format_id"])
        format_value = str(row["format"])
        packaging_value = str(row["packaging"])

        present_count = sum(1 for website_id in website_ids if (product_format_id, website_id) in presence_pairs)
        missing_count = max(0, website_count - present_count)
        coverage_rate = round((present_count / website_count) * 100, 2) if website_count else 0.0
        presence_status = _resolve_presence_status(present_count, website_count)

        product_rows_map[product_id]["formats"].append(
            {
                "product_format_id": product_format_id,
                "format": format_value,
                "packaging": packaging_value,
                "format_label": f"{format_value} {packaging_value}",
                "presence_status": presence_status,
                "present_count": present_count,
                "missing_count": missing_count,
                "coverage_rate": coverage_rate,
                "cells": [
                    {
                        "website_id": website_id,
                        "present": (product_format_id, website_id) in presence_pairs,
                    }
                    for website_id in website_ids
                ],
            }
        )

    for product_row in product_rows:
        format_rows = product_row["formats"]
        product_row["total_formats"] = len(format_rows)
        product_row["present_formats"] = sum(1 for row in format_rows if row["present_count"] > 0)
        product_row["presence_status"] = _resolve_family_status(format_rows)

    total_formats = sum(len(row["formats"]) for row in product_rows)
    total_matrix_cells = total_formats * website_count
    present_cells = sum(format_row["present_count"] for product_row in product_rows for format_row in product_row["formats"])
    missing_cells = max(0, total_matrix_cells - present_cells)
    coverage_rate = round((present_cells / total_matrix_cells) * 100, 2) if total_matrix_cells else 0.0

    return {
        "country": selected_country,
        "available_countries": available_countries,
        "country_retailers": country_retailers,
        "websites": websites,
        "kpis": {
            "total_product_families": len(product_rows),
            "total_formats": total_formats,
            "total_websites": website_count,
            "total_active_links": total_active_links,
            "total_matrix_cells": total_matrix_cells,
            "present_cells": present_cells,
            "missing_cells": missing_cells,
            "coverage_rate": coverage_rate,
        },
        "rows": product_rows,
    }


def get_retail_presence_country_metrics() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*)::int AS total_formats
                FROM product_variants
                """
            )
            total_formats = int((cur.fetchone() or {}).get("total_formats", 0) or 0)

            cur.execute(
                """
                SELECT
                    w.country AS country,
                    COUNT(DISTINCT w.id)::int AS websites_count,
                    COUNT(DISTINCT (pu.product_variant_id, pu.website_id))::int AS present_cells,
                    COUNT(*) FILTER (WHERE pu.is_active = TRUE)::int AS total_active_links
                FROM websites w
                LEFT JOIN product_urls pu
                    ON pu.website_id = w.id
                    AND pu.is_active = TRUE
                WHERE w.country IS NOT NULL AND BTRIM(w.country) <> ''
                GROUP BY w.country
                ORDER BY w.country
                """
            )
            rows = cur.fetchall()

    metrics: list[dict] = []
    for row in rows:
        country = str(row.get("country") or "").strip()
        if not country:
            continue

        websites_count = int(row.get("websites_count") or 0)
        present_cells = int(row.get("present_cells") or 0)
        total_active_links = int(row.get("total_active_links") or 0)

        total_matrix_cells = total_formats * websites_count
        coverage_rate = round((present_cells / total_matrix_cells) * 100, 2) if total_matrix_cells else 0.0

        metrics.append(
            {
                "country": country,
                "iso3": country_name_to_iso3(country),
                "websites_count": websites_count,
                "total_formats": total_formats,
                "present_cells": present_cells,
                "total_matrix_cells": total_matrix_cells,
                "coverage_rate": coverage_rate,
                "total_active_links": total_active_links,
            }
        )

    return metrics
