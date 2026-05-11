from database.database_config import get_connection
from etl.parsers.citygross import parse_citygross_price
from etl.parsers.coop import parse_coop_price
from etl.parsers.ica import parse_ica_price
from etl.parsers.kesko import parse_kesko_price
from etl.parsers.sok import parse_sok_price

PARSERS = {
    "citygross": parse_citygross_price,
    "coop":      parse_coop_price,
    "ica":       parse_ica_price,
    "kesko":     parse_kesko_price,
    "sok":       parse_sok_price,

}


def _to_price_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return round(float(str(value).replace(",", ".").replace(":", ".")), 2)


def _normalize_parser_result(result):
    """Normalize parser output into current/base prices.

    Supported formats:
    - (price, currency)
    - { current_price, base_price, is_discounted, currency }
    """
    if result is None:
        return None

    if isinstance(result, dict):
        current_price = _to_price_float(result.get("current_price"))
        base_price = _to_price_float(result.get("base_price"))
        currency = str(result.get("currency") or "").strip().upper() or "EUR"
        is_discounted_raw = result.get("is_discounted")
        is_discounted = bool(is_discounted_raw) if is_discounted_raw is not None else None

        if current_price is None:
            return None
        if base_price is None:
            base_price = current_price
        if is_discounted is None:
            is_discounted = bool(current_price < base_price)

        return current_price, base_price, is_discounted, currency

    if isinstance(result, (tuple, list)) and len(result) == 2:
        price, currency = result
        current_price = _to_price_float(price)
        if current_price is None:
            return None
        return current_price, current_price, False, (str(currency or "").strip().upper() or "EUR")

    return None


def _resolve_fallback_currency(cursor, website_id, store_id, product_variant_id, week_start):
    cursor.execute(
        """
        SELECT currency
        FROM scraped_prices
                WHERE product_variant_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND date_trunc('week', observed_at)::date <= %s::date
        ORDER BY observed_at DESC
        LIMIT 1
        """,
                (product_variant_id, website_id, store_id, week_start),
    )
    latest_scraped = cursor.fetchone()
    if latest_scraped and latest_scraped[0]:
        return latest_scraped[0]

    cursor.execute(
        """
        SELECT currency
        FROM weekly_price_summary
                WHERE product_variant_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND week_start <= %s::date
        ORDER BY week_start DESC, updated_at DESC, id DESC
        LIMIT 1
        """,
                (product_variant_id, website_id, store_id, week_start),
    )
    latest_summary = cursor.fetchone()
    if latest_summary and latest_summary[0]:
        return latest_summary[0]

    return "EUR"


def _refresh_weekly_summary(cursor, website_id, store_id, product_variant_id, week_start):
    cursor.execute(
        """
        SELECT id, data_status, currency
        FROM weekly_price_summary
                WHERE product_variant_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND week_start = %s::date
        """,
                (product_variant_id, website_id, store_id, week_start),
    )
    existing = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            ROUND(AVG(current_price)::NUMERIC, 2) AS avg_price,
            COUNT(*)::INTEGER AS sample_count
        FROM scraped_prices
                WHERE product_variant_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND date_trunc('week', observed_at)::date = %s::date
        """,
                (product_variant_id, website_id, store_id, week_start),
    )
    agg_row = cursor.fetchone()
    if not agg_row:
        return

    avg_price, sample_count = agg_row

    if not sample_count:
        if existing and existing[1] in ("OK", "PARTIAL"):
            return

        resolved_currency = existing[2] if existing and existing[2] else _resolve_fallback_currency(
            cursor,
            website_id,
            store_id,
            product_variant_id,
            week_start,
        )

        if existing:
            cursor.execute(
                """
                UPDATE weekly_price_summary
                SET avg_price = NULL,
                    sample_count = 0,
                    currency = %s,
                    data_status = 'MISSING',
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    resolved_currency,
                    existing[0],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO weekly_price_summary
                (
                    product_variant_id,
                    website_id,
                    store_id,
                    week_start,
                    avg_price,
                    sample_count,
                    currency,
                    data_status
                )
                VALUES (%s, %s, %s, %s::date, %s, %s, %s, %s)
                """,
                (
                    product_variant_id,
                    website_id,
                    store_id,
                    week_start,
                    None,
                    0,
                    resolved_currency,
                    "MISSING",
                ),
            )
        return

    cursor.execute(
        """
        SELECT currency
        FROM scraped_prices
                WHERE product_variant_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND date_trunc('week', observed_at)::date = %s::date
        ORDER BY observed_at DESC
        LIMIT 1
        """,
                (product_variant_id, website_id, store_id, week_start),
    )
    latest_row = cursor.fetchone()
    currency = latest_row[0] if latest_row else "EUR"

    if existing:
        cursor.execute(
            """
            UPDATE weekly_price_summary
            SET avg_price = %s,
                sample_count = %s,
                currency = %s,
                data_status = 'OK',
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                avg_price,
                sample_count,
                currency,
                existing[0],
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO weekly_price_summary
            (
                product_variant_id,
                website_id,
                store_id,
                week_start,
                avg_price,
                sample_count,
                currency,
                data_status
            )
            VALUES (%s, %s, %s, %s::date, %s, %s, %s, %s)
            """,
            (
                product_variant_id,
                website_id,
                store_id,
                week_start,
                avg_price,
                sample_count,
                currency,
                "OK",
            ),
        )

def run_etl(raw_ids=None):
    scoped_raw_ids = None
    if raw_ids is not None:
        scoped_raw_ids = [int(raw_id) for raw_id in raw_ids if raw_id is not None]
        if not scoped_raw_ids:
            return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            where_clause = "WHERE rs.status = 'pending'"
            params = []
            if scoped_raw_ids is not None:
                where_clause += " AND rs.id = ANY(%s)"
                params.append(scoped_raw_ids)

            cursor.execute(
                f"""
                SELECT
                    rs.id,
                    pu.website_id,
                    pu.store_id,
                    pu.product_variant_id,
                    rs.payload,
                    rs.scraped_at,
                    date_trunc('week', rs.scraped_at)::date AS week_start,
                    w.site_name,
                    rs.screenshot_path
                FROM raw_staging rs
                JOIN product_urls pu ON rs.product_url_id = pu.id
                JOIN websites w      ON pu.website_id     = w.id
                {where_clause}
                ORDER BY rs.scraped_at ASC
                """,
                tuple(params),
            )
            rows = cursor.fetchall()

            touched_week_keys = set()
            processed_raw_ids = []

            for row in rows:
                raw_id, website_id, store_id, product_variant_id, payload, scraped_at, week_start, site_name, screenshot_path = row
                touched_week_keys.add((website_id, store_id, product_variant_id, week_start))

                parser = PARSERS.get((site_name or "").strip().lower())
                if not parser:
                    cursor.execute(
                        "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                        (f"No parser for {site_name}", raw_id),
                    )
                    continue

                result = parser(payload)

                try:
                    normalized = _normalize_parser_result(result)
                except (ValueError, TypeError) as exc:
                    cursor.execute(
                        "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                        (f"Price conversion error: {str(exc)}", raw_id),
                    )
                    continue

                if normalized:
                    current_price, base_price, is_discounted, currency = normalized
                    if current_price <= 0:
                        cursor.execute(
                            "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                            (f"Invalid current_price: {current_price} (must be > 0)", raw_id),
                        )
                        continue

                    if base_price <= 0:
                        cursor.execute(
                            "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                            (f"Invalid base_price: {base_price} (must be > 0)", raw_id),
                        )
                        continue

                    cursor.execute(
                        """
                        INSERT INTO scraped_prices
                        (raw_staging_id, product_variant_id, website_id, store_id, current_price, base_price, is_discounted, currency, screenshot_path, observed_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (raw_staging_id) DO NOTHING
                        """,
                        (
                            raw_id,
                            product_variant_id,
                            website_id,
                            store_id,
                            current_price,
                            base_price,
                            is_discounted,
                            currency or "EUR",
                            screenshot_path,
                            scraped_at,
                        ),
                    )

                    processed_raw_ids.append(raw_id)
                else:
                    cursor.execute(
                        "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                        ("Price not found by parser", raw_id),
                    )

            for website_id, store_id, product_variant_id, week_start in touched_week_keys:
                _refresh_weekly_summary(cursor, website_id, store_id, product_variant_id, week_start)

            for raw_id in processed_raw_ids:
                cursor.execute(
                    "UPDATE raw_staging SET status = 'processed', processed_at = NOW() WHERE id = %s",
                    (raw_id,),
                )

            conn.commit()


if __name__ == "__main__":
    run_etl()