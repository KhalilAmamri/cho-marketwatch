import psycopg2
from database.database_config import DATABASE_CONFIG


def get_connection():
    return psycopg2.connect(
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"],
        database=DATABASE_CONFIG["database"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
    )


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
            pt.product_type,
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
        JOIN product_types pt    ON p.product_type_id = pt.id
        JOIN categories c        ON p.category_id = c.id
        JOIN ranges r            ON p.range_id = r.id
        JOIN websites w          ON pu.website_id  = w.id
        LEFT JOIN stores s       ON pu.store_id    = s.id
        WHERE w.site_name = %s AND pu.is_active = TRUE
        ORDER BY b.brand_name ASC, pt.product_type ASC, c.category_name ASC, r.range_name ASC, pv.format ASC
        """,
        (site_name,),
    )
    return cursor.fetchall()


def insert_raw_staging(cursor, product_url_id, payload, status, http_status, error_message):
    cursor.execute(
        """
        INSERT INTO raw_staging
        (product_url_id, payload, status, http_status_code, error_message, scraped_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """,
        (product_url_id, payload, status, http_status, error_message),
    )