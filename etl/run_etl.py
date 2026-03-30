import psycopg2

from database.database_config import DATABASE_CONFIG
from etl.parsers.citygross import parse_citygross_price
from etl.parsers.coop import parse_coop_price
from etl.parsers.ica import parse_ica_price
from etl.parsers.kesko import parse_kesko_price
from etl.parsers.sok import parse_sok_price


def get_connection():
    return psycopg2.connect(
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"],
        database=DATABASE_CONFIG["database"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
    )

PARSERS = {
    "Citygross": parse_citygross_price,
    "Coop":      parse_coop_price,
    "Ica":       parse_ica_price,
    "Kesko":     parse_kesko_price,
    "Sok":       parse_sok_price,

}

def run_etl():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT rs.id, pu.website_id, pu.store_id, pu.product_format_id, rs.payload, rs.scraped_at, w.site_name
                FROM raw_staging rs
                JOIN product_urls pu ON rs.product_url_id = pu.id
                JOIN websites w      ON pu.website_id     = w.id
                WHERE rs.status = 'pending'
                ORDER BY rs.scraped_at ASC
                """
            )
            rows = cursor.fetchall()

            for row in rows:
                raw_id, website_id, store_id, product_format_id, payload, scraped_at, site_name = row

                parser = PARSERS.get(site_name)
                if not parser:
                    cursor.execute(
                        "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                        (f"No parser for {site_name}", raw_id),
                    )
                    conn.commit()
                    continue

                result = parser(payload)

                if result:
                    price, currency = result
                    try:
                        price_float = float(str(price).replace(",", "."))

                        if price_float <= 0:
                            cursor.execute(
                                "UPDATE raw_staging SET status = 'failed', error_message = %s WHERE id = %s",
                                (f"Invalid price: {price_float} (must be > 0)", raw_id),
                            )
                            conn.commit()
                            continue

                        cursor.execute(
                            """
                            INSERT INTO price_history
                            (product_format_id, website_id, store_id, price, currency, scraped_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (product_format_id, website_id, store_id, price_float, currency, scraped_at),
                        )
                        cursor.execute(
                            "UPDATE raw_staging SET status = 'processed', processed_at = NOW() WHERE id = %s",
                            (raw_id,),
                        )

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

                conn.commit()


if __name__ == "__main__":
    run_etl()