import psycopg2
from database.database_config import get_connection


_supports_screenshot_column = None


def get_all_websites(cursor):
    cursor.execute(
        "SELECT site_name FROM websites ORDER BY site_name ASC"
    )
    return cursor.fetchall()


def get_product_urls(cursor, site_name):
    cursor.execute(
        """
        SELECT
            pu.id,
            pv.id             AS product_format_id,
            b.brand_name,
            c.category_name,
            r.range_name,
            pv.format,
            pv.packaging,
            pu.url,
            pu.store_id,
            s.store_code
        FROM product_urls pu
        JOIN product_formats pv ON pu.product_format_id  = pv.id
        JOIN products p          ON pv.product_id  = p.id
        JOIN brands b            ON p.brand_id     = b.id
        JOIN categories c        ON p.category_id = c.id
        JOIN ranges r            ON p.range_id = r.id
        JOIN websites w          ON pu.website_id  = w.id
        LEFT JOIN stores s       ON pu.store_id    = s.id
        WHERE w.site_name = %s AND pu.is_active = TRUE
        ORDER BY b.brand_name ASC, c.category_name ASC, r.range_name ASC, pv.format ASC
        """,
        (site_name,),
    )
    return cursor.fetchall()


def insert_raw_staging(cursor, product_url_id, payload, status, http_status, error_message, screenshot_path=None):
    global _supports_screenshot_column

    if _supports_screenshot_column is False:
        cursor.execute(
            """
            INSERT INTO raw_staging
            (product_url_id, payload, status, http_status_code, error_message, scraped_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (product_url_id, payload, status, http_status, error_message),
        )
        return

    try:
        cursor.execute(
            """
            INSERT INTO raw_staging
            (product_url_id, payload, status, http_status_code, error_message, screenshot_path, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (product_url_id, payload, status, http_status, error_message, screenshot_path),
        )
        _supports_screenshot_column = True
    except psycopg2.errors.UndefinedColumn:
        # Backward compatibility for existing DBs before migration.
        cursor.connection.rollback()
        _supports_screenshot_column = False
        cursor.execute(
            """
            INSERT INTO raw_staging
            (product_url_id, payload, status, http_status_code, error_message, scraped_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (product_url_id, payload, status, http_status, error_message),
        )