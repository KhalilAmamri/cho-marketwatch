import psycopg2
from database.database_config import get_connection


_supports_screenshot_column = None


def get_all_websites(cursor):
    cursor.execute(
        "SELECT site_name FROM websites ORDER BY site_name ASC"
    )
    return cursor.fetchall()


def get_product_urls(cursor, site_name, product_url_id=None):
    filters = ["w.site_name = %s", "pu.is_active = TRUE"]
    params = [site_name]
    if product_url_id is not None:
        filters.append("pu.id = %s")
        params.append(int(product_url_id))

    cursor.execute(
        f"""
        SELECT
            pu.id,
            pv.id             AS product_variant_id,
            b.brand_name,
            c.category_name,
            r.range_name,
            f.format_name     AS format,
            pk.packaging_name AS packaging,
            pu.url,
            pu.store_id,
            s.store_code
        FROM product_urls pu
        JOIN product_variants pv ON pu.product_variant_id = pv.id
        JOIN formats f           ON pv.format_id          = f.id
        JOIN packagings pk       ON pv.packaging_id       = pk.id
        JOIN products p          ON pv.product_id  = p.id
        JOIN brands b            ON p.brand_id     = b.id
        JOIN categories c        ON p.category_id = c.id
        JOIN ranges r            ON p.range_id = r.id
        JOIN websites w          ON pu.website_id  = w.id
        LEFT JOIN stores s       ON pu.store_id    = s.id
        WHERE {' AND '.join(filters)}
        ORDER BY b.brand_name ASC, c.category_name ASC, r.range_name ASC, f.format_name ASC
        """,
        tuple(params),
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
            RETURNING id
            """,
            (product_url_id, payload, status, http_status, error_message),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None

    try:
        cursor.execute(
            """
            INSERT INTO raw_staging
            (product_url_id, payload, status, http_status_code, error_message, screenshot_path, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (product_url_id, payload, status, http_status, error_message, screenshot_path),
        )
        row = cursor.fetchone()
        _supports_screenshot_column = True
        return int(row[0]) if row else None
    except psycopg2.errors.UndefinedColumn:
        # Backward compatibility for existing DBs before migration.
        cursor.connection.rollback()
        _supports_screenshot_column = False
        cursor.execute(
            """
            INSERT INTO raw_staging
            (product_url_id, payload, status, http_status_code, error_message, scraped_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (product_url_id, payload, status, http_status, error_message),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None