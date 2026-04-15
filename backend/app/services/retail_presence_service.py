from collections import OrderedDict

from psycopg2.extras import RealDictCursor

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
    selected_country: str,
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

            selected_country: str
            if country:
                selected_country = country.strip()
                if available_countries and selected_country not in available_countries:
                    raise ValueError(f"Unknown country '{selected_country}'")
            else:
                if "Sweden" in available_countries:
                    selected_country = "Sweden"
                elif available_countries:
                    selected_country = available_countries[0]
                else:
                    selected_country = "Unknown"

            cur.execute(
                """
                SELECT
                    p.id AS product_id,
                    b.brand_name,
                    c.category_name,
                    r.range_name,
                    pf.id AS product_format_id,
                    pf.format,
                    pf.packaging
                FROM products p
                JOIN brands b ON p.brand_id = b.id
                JOIN categories c ON p.category_id = c.id
                JOIN ranges r ON p.range_id = r.id
                JOIN product_formats pf ON pf.product_id = p.id
                ORDER BY b.brand_name, c.category_name, r.range_name, pf.format, pf.packaging
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

            cur.execute(
                """
                SELECT id AS website_id, site_name, country
                FROM websites
                WHERE country = %s
                ORDER BY site_name
                """,
                (selected_country,),
            )
            websites = cur.fetchall()
            website_ids = [int(row["website_id"]) for row in websites]

            if not website_ids:
                return _build_empty_response(selected_country, available_countries, country_retailers, product_rows)

            cur.execute(
                """
                SELECT DISTINCT pu.product_format_id, pu.website_id
                FROM product_urls pu
                JOIN websites w ON pu.website_id = w.id
                WHERE pu.is_active = TRUE
                  AND w.country = %s
                """,
                (selected_country,),
            )
            presence_pairs = {
                (int(row["product_format_id"]), int(row["website_id"])) for row in cur.fetchall()
            }

            cur.execute(
                """
                SELECT COUNT(*)::int AS total
                FROM product_urls pu
                JOIN websites w ON pu.website_id = w.id
                WHERE pu.is_active = TRUE
                  AND w.country = %s
                """,
                (selected_country,),
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
