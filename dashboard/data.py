import pandas as pd
from database.database_config import get_connection


PRODUCT_LABEL_SQL = (
    "b.brand_name || ' ' || c.category_name || ' ' || r.range_name || ' ' || pf.format || ' ' || pf.packaging"
)

PRICE_EUR_SQL = """
CASE
    WHEN ws.currency = 'EUR' THEN ROUND(ws.avg_price::NUMERIC, 2)
    WHEN fx_hist.rate_to_eur IS NOT NULL THEN ROUND((ws.avg_price / fx_hist.rate_to_eur)::NUMERIC, 2)
    ELSE NULL
END
"""


def get_last_update_timestamp():
    query = """
    SELECT MAX(ws.week_start)::timestamp AS last_updated
    FROM weekly_price_summary ws
    """
    with get_connection() as conn:
        df = pd.read_sql(query, conn)

    if df.empty:
        return None

    last_updated = pd.to_datetime(df.loc[0, "last_updated"], errors="coerce")
    if pd.isna(last_updated):
        return None
    return last_updated


def get_weekly_price_points():
    query = f"""
    SELECT
        {PRODUCT_LABEL_SQL} AS product,
        w.site_name AS website,
        w.country AS country,
        CASE
            WHEN s.store_code IS NOT NULL
            THEN w.site_name || ' (' || s.store_code || ')'
            ELSE w.site_name
        END AS store,
        ws.avg_price AS price,
        ws.currency,
        sp_latest.screenshot_path,
        ws.week_start::timestamp AS scraped_at,
        {PRICE_EUR_SQL} AS price_eur,
        pu.url AS product_url
    FROM weekly_price_summary ws
    JOIN product_formats pf ON ws.product_format_id = pf.id
    JOIN products p         ON pf.product_id = p.id
    JOIN brands b           ON p.brand_id = b.id
    JOIN categories c       ON p.category_id = c.id
    JOIN ranges r           ON p.range_id = r.id
    JOIN websites w         ON ws.website_id = w.id
    LEFT JOIN stores s      ON ws.store_id = s.id
    JOIN product_urls pu    ON pu.product_format_id = pf.id
                           AND pu.website_id = ws.website_id
                           AND pu.store_id IS NOT DISTINCT FROM ws.store_id
    LEFT JOIN LATERAL (
        SELECT sp.screenshot_path
        FROM scraped_prices sp
        WHERE sp.product_format_id = ws.product_format_id
          AND sp.website_id = ws.website_id
          AND sp.store_id IS NOT DISTINCT FROM ws.store_id
          AND date_trunc('week', sp.observed_at)::date = ws.week_start
          AND sp.screenshot_path IS NOT NULL
        ORDER BY sp.observed_at DESC
        LIMIT 1
    ) sp_latest ON TRUE
    LEFT JOIN LATERAL (
        SELECT rate_to_eur FROM exchange_rates
        WHERE currency = ws.currency AND date <= ws.week_start
        ORDER BY date DESC LIMIT 1
    ) fx_hist ON TRUE
    ORDER BY ws.week_start DESC, pf.id, w.site_name, ws.store_id
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)


def get_products_list():
    query = f"""
    SELECT DISTINCT
        {PRODUCT_LABEL_SQL} AS label
    FROM product_formats pf
    JOIN products p ON pf.product_id = p.id
    JOIN brands b   ON p.brand_id    = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    ORDER BY 1
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)


def get_price_history(product_label):
    query = f"""
    SELECT
        {PRICE_EUR_SQL} AS price,
        ws.week_start::timestamp AS scraped_at,
        CASE
            WHEN s.store_code IS NOT NULL
            THEN w.site_name || ' (' || s.store_code || ')'
            ELSE w.site_name
        END AS store
    FROM weekly_price_summary ws
    JOIN product_formats pf ON ws.product_format_id  = pf.id
    JOIN products p         ON pf.product_id = p.id
    JOIN brands b           ON p.brand_id    = b.id
    JOIN categories c       ON p.category_id = c.id
    JOIN websites w         ON ws.website_id = w.id
    LEFT JOIN stores s      ON ws.store_id   = s.id
    LEFT JOIN LATERAL (
        SELECT rate_to_eur FROM exchange_rates
        WHERE currency = ws.currency AND date <= ws.week_start
        ORDER BY date DESC LIMIT 1
    ) fx_hist ON TRUE
    JOIN ranges r           ON p.range_id = r.id
    WHERE {PRODUCT_LABEL_SQL} = %s
    ORDER BY ws.week_start ASC, ws.store_id ASC
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(product_label,))


def get_saved_forecasts(product_label):
    query = f"""
    SELECT
        af.forecast_date::timestamp AS date,
        af.predicted_price AS price_pred,
        af.price_low,
        af.price_high,
        af.confidence_level,
        af.training_points,
        CASE
            WHEN s.store_code IS NOT NULL
            THEN w.site_name || ' (' || s.store_code || ')'
            ELSE w.site_name
        END AS store
    FROM price_forecasts af
    JOIN product_formats pf ON af.product_format_id = pf.id
    JOIN products p         ON pf.product_id = p.id
    JOIN brands b           ON p.brand_id = b.id
    JOIN categories c       ON p.category_id = c.id
    JOIN ranges r           ON p.range_id = r.id
    JOIN websites w         ON af.website_id = w.id
    LEFT JOIN stores s      ON af.store_id = s.id
    WHERE {PRODUCT_LABEL_SQL} = %s
    ORDER BY af.forecast_date ASC
    """

    try:
        with get_connection() as conn:
            return pd.read_sql(query, conn, params=(product_label,))
    except Exception:
        return pd.DataFrame(
            columns=[
                "date",
                "price_pred",
                "price_low",
                "price_high",
                "confidence_level",
                "training_points",
                "store",
            ]
        )


def get_store_comparison(product_label):
    query = f"""
    SELECT DISTINCT ON (w.site_name, ws.store_id)
        CASE
            WHEN s.store_code IS NOT NULL
            THEN w.site_name || ' (' || s.store_code || ')'
            ELSE w.site_name
        END AS store,
        w.country AS country,
        ws.avg_price AS price_original,
        ws.currency,
        ws.week_start::timestamp AS scraped_at,
        {PRICE_EUR_SQL} AS price_eur
    FROM weekly_price_summary ws
    JOIN product_formats pf ON ws.product_format_id = pf.id
    JOIN products p          ON pf.product_id = p.id
    JOIN brands b            ON p.brand_id    = b.id
    JOIN categories c        ON p.category_id = c.id
    JOIN websites w          ON ws.website_id = w.id
    LEFT JOIN stores s       ON ws.store_id   = s.id
    LEFT JOIN LATERAL (
        SELECT rate_to_eur FROM exchange_rates
        WHERE currency = ws.currency AND date <= ws.week_start
        ORDER BY date DESC LIMIT 1
    ) fx_hist ON TRUE
    JOIN ranges r           ON p.range_id = r.id
    WHERE {PRODUCT_LABEL_SQL} = %s
    ORDER BY w.site_name, ws.store_id, ws.week_start DESC
    """
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(product_label,))
    return df.sort_values("price_eur")


def get_failed_scrapes_summary():
    query = """
    SELECT
        w.site_name,
        w.country,
        b.brand_name,
        c.category_name,
        r.range_name,
        pf.format,
        pf.packaging,
        pu.url,
        MAX(rs.error_message) AS last_error,
        MAX(rs.http_status_code) AS last_status_code,
        COUNT(*) AS fail_count
    FROM raw_staging rs
    JOIN product_urls pu   ON rs.product_url_id = pu.id
    JOIN product_formats pf ON pu.product_format_id = pf.id
    JOIN products p        ON pf.product_id = p.id
    JOIN brands b          ON p.brand_id = b.id
    JOIN categories c      ON p.category_id = c.id
    JOIN ranges r          ON p.range_id = r.id
    JOIN websites w        ON pu.website_id = w.id
    WHERE rs.status = 'failed'
    GROUP BY w.site_name, w.country, b.brand_name, c.category_name, r.range_name, pf.format, pf.packaging, pu.url
    HAVING COUNT(*) > 0
    ORDER BY fail_count DESC
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)