from database.database_config import get_connection
from etl.parsers.citygross import parse_citygross_price
from etl.parsers.coop import parse_coop_price
from etl.parsers.ica import parse_ica_price
from etl.parsers.kesko import parse_kesko_price
from etl.parsers.sok import parse_sok_price

PARSERS = {
    "Citygross": parse_citygross_price,
    "Coop":      parse_coop_price,
    "Ica":       parse_ica_price,
    "Kesko":     parse_kesko_price,
    "Sok":       parse_sok_price,

}


def _refresh_weekly_summary(cursor, website_id, store_id, product_format_id, week_start):
    cursor.execute(
        """
        SELECT
            ROUND(AVG(price)::NUMERIC, 2) AS avg_price,
            COUNT(*)::INTEGER AS sample_count
        FROM scraped_prices
        WHERE product_format_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND date_trunc('week', observed_at)::date = %s::date
        """,
        (product_format_id, website_id, store_id, week_start),
    )
    agg_row = cursor.fetchone()
    if not agg_row:
        return

    avg_price, sample_count = agg_row
    if not sample_count:
        return

    cursor.execute(
        """
        SELECT currency
        FROM scraped_prices
        WHERE product_format_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND date_trunc('week', observed_at)::date = %s::date
        ORDER BY observed_at DESC
        LIMIT 1
        """,
        (product_format_id, website_id, store_id, week_start),
    )
    latest_row = cursor.fetchone()
    currency = latest_row[0] if latest_row else "EUR"

    cursor.execute(
        """
        SELECT id
        FROM weekly_price_summary
        WHERE product_format_id = %s
          AND website_id = %s
          AND store_id IS NOT DISTINCT FROM %s
          AND week_start = %s::date
        """,
        (product_format_id, website_id, store_id, week_start),
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE weekly_price_summary
            SET avg_price = %s,
                sample_count = %s,
                currency = %s,
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
                product_format_id,
                website_id,
                store_id,
                week_start,
                avg_price,
                sample_count,
                currency
            )
            VALUES (%s, %s, %s, %s::date, %s, %s, %s)
            """,
            (
                product_format_id,
                website_id,
                store_id,
                week_start,
                avg_price,
                sample_count,
                currency,
            ),
        )

def run_etl():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    rs.id,
                    pu.website_id,
                    pu.store_id,
                    pu.product_format_id,
                    rs.payload,
                    rs.scraped_at,
                    date_trunc('week', rs.scraped_at)::date AS week_start,
                    w.site_name,
                    rs.screenshot_path
                FROM raw_staging rs
                JOIN product_urls pu ON rs.product_url_id = pu.id
                JOIN websites w      ON pu.website_id     = w.id
                WHERE rs.status = 'pending'
                ORDER BY rs.scraped_at ASC
                """
            )
            rows = cursor.fetchall()

            touched_week_keys = set()
            processed_raw_ids = []

            for row in rows:
                raw_id, website_id, store_id, product_format_id, payload, scraped_at, week_start, site_name, screenshot_path = row

                parser = PARSERS.get(site_name)
                if not parser:
                    cursor.execute(
                        "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                        (f"No parser for {site_name}", raw_id),
                    )
                    continue

                result = parser(payload)

                if result:
                    price, currency = result
                    try:
                        price_float = round(float(str(price).replace(",", ".")), 2)

                        if price_float <= 0:
                            cursor.execute(
                                "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                                (f"Invalid price: {price_float} (must be > 0)", raw_id),
                            )
                            continue

                        cursor.execute(
                            """
                            INSERT INTO scraped_prices
                            (raw_staging_id, product_format_id, website_id, store_id, price, currency, screenshot_path, observed_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (raw_staging_id) DO NOTHING
                            """,
                            (
                                raw_id,
                                product_format_id,
                                website_id,
                                store_id,
                                price_float,
                                currency or "EUR",
                                screenshot_path,
                                scraped_at,
                            ),
                        )

                        touched_week_keys.add((website_id, store_id, product_format_id, week_start))
                        processed_raw_ids.append(raw_id)

                    except ValueError as exc:
                        cursor.execute(
                            "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                            (f"Price conversion error: {str(exc)}", raw_id),
                        )
                else:
                    cursor.execute(
                        "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                        ("Price not found by parser", raw_id),
                    )

            for website_id, store_id, product_format_id, week_start in touched_week_keys:
                _refresh_weekly_summary(cursor, website_id, store_id, product_format_id, week_start)

            for raw_id in processed_raw_ids:
                cursor.execute(
                    "UPDATE raw_staging SET status = 'processed', processed_at = NOW() WHERE id = %s",
                    (raw_id,),
                )

            conn.commit()


if __name__ == "__main__":
    run_etl()