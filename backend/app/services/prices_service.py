from datetime import date
from psycopg2.extras import RealDictCursor

from app.db.connection import get_connection

PRODUCT_LABEL_SQL = (
    "b.brand_name || ' ' || c.category_name || ' ' || r.range_name || ' ' || pf.format || ' ' || pf.packaging"
)

STORE_LABEL_SQL = """
CASE
    WHEN s.store_code IS NOT NULL THEN w.site_name || ' (' || s.store_code || ')'
    ELSE w.site_name
END
"""

PRICE_EUR_SQL = """
CASE
    WHEN ws.currency = 'EUR' THEN ROUND(ws.avg_price::NUMERIC, 2)
    WHEN fx_hist.rate_to_eur IS NOT NULL THEN ROUND((ws.avg_price / fx_hist.rate_to_eur)::NUMERIC, 2)
    ELSE NULL
END
"""


def _to_float(value):
    return float(value) if value is not None else None


def get_kpis():
    query = """
    SELECT
        MAX(week_start) AS latest_week_start,
        MAX(updated_at) AS last_refreshed_at,
        MAX(week_start)::timestamp AS last_update,
        COUNT(DISTINCT product_format_id) AS products_tracked,
        COUNT(DISTINCT website_id) AS websites_tracked,
        COUNT(DISTINCT COALESCE(store_id, -1)) AS stores_tracked,
        COUNT(*) FILTER (WHERE week_start = (SELECT MAX(week_start) FROM weekly_price_summary)) AS latest_week_records
    FROM weekly_price_summary
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            row = cur.fetchone()
    return row


def get_filters():
    query = f"""
    SELECT DISTINCT {PRODUCT_LABEL_SQL} AS product
    FROM product_formats pf
    JOIN products p ON pf.product_id = p.id
    JOIN brands b ON p.brand_id = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    ORDER BY 1
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            products = [r["product"] for r in cur.fetchall()]

            cur.execute("SELECT DISTINCT site_name FROM websites ORDER BY 1")
            websites = [r["site_name"] for r in cur.fetchall()]

            cur.execute("SELECT DISTINCT country FROM websites WHERE country IS NOT NULL ORDER BY 1")
            countries = [r["country"] for r in cur.fetchall()]

            cur.execute("SELECT DISTINCT currency FROM weekly_price_summary ORDER BY 1")
            currencies = [r["currency"] for r in cur.fetchall()]

    return {
        "products": products,
        "websites": websites,
        "countries": countries,
        "currencies": currencies,
    }


def get_summary(week_start: date | None = None, all_weeks: bool = False):
    where_clause = ""
    params = []
    if week_start:
        where_clause = "WHERE ws.week_start = %s"
        params.append(week_start)
    elif not all_weeks:
        where_clause = "WHERE ws.week_start = (SELECT MAX(week_start) FROM weekly_price_summary)"

    query = f"""
    SELECT
        {PRODUCT_LABEL_SQL} AS product,
        w.site_name AS website,
        w.country AS country,
        {STORE_LABEL_SQL} AS store,
        ws.currency,
        ws.avg_price AS price,
        {PRICE_EUR_SQL} AS price_eur,
        source_link.url AS source_url,
        latest_shot.screenshot_path AS screenshot_path,
        ws.week_start
    FROM weekly_price_summary ws
    JOIN product_formats pf ON ws.product_format_id = pf.id
    JOIN products p ON pf.product_id = p.id
    JOIN brands b ON p.brand_id = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    JOIN websites w ON ws.website_id = w.id
    LEFT JOIN stores s ON ws.store_id = s.id
        LEFT JOIN LATERAL (
                SELECT pu.url
                FROM product_urls pu
                WHERE pu.website_id = ws.website_id
                    AND pu.product_format_id = ws.product_format_id
                    AND pu.store_id IS NOT DISTINCT FROM ws.store_id
                    AND pu.url IS NOT NULL
                    AND BTRIM(pu.url) <> ''
                ORDER BY pu.is_active DESC, pu.created_at DESC, pu.id DESC
                LIMIT 1
        ) source_link ON TRUE
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = ws.currency AND date <= ws.week_start
        ORDER BY date DESC LIMIT 1
    ) fx_hist ON TRUE
    LEFT JOIN LATERAL (
        SELECT sp.screenshot_path
        FROM scraped_prices sp
        WHERE sp.product_format_id = ws.product_format_id
          AND sp.website_id = ws.website_id
          AND sp.store_id IS NOT DISTINCT FROM ws.store_id
          AND date_trunc('week', sp.observed_at)::date = ws.week_start
          AND sp.screenshot_path IS NOT NULL
          AND BTRIM(sp.screenshot_path) <> ''
        ORDER BY sp.observed_at DESC
        LIMIT 1
    ) latest_shot ON TRUE
    {where_clause}
    ORDER BY product, website, store
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    for row in rows:
        row["price"] = _to_float(row["price"])
        row["price_eur"] = _to_float(row["price_eur"])

    return rows


def get_timeseries(
    product: str,
    website: str | None = None,
    country: str | None = None,
    weeks: int = 52,
    store: str | None = None,
):
    filters = [f"{PRODUCT_LABEL_SQL} = %s"]
    params = [product]

    if website:
        filters.append("w.site_name = %s")
        params.append(website)

    if country:
        filters.append("w.country = %s")
        params.append(country)

    if store:
        filters.append(f"{STORE_LABEL_SQL} = %s")
        params.append(store)

    where_clause = " AND ".join(filters)
    params.append(weeks)

    query = f"""
    WITH base AS (
        SELECT
            ws.week_start,
            {PRICE_EUR_SQL} AS price_eur
        FROM weekly_price_summary ws
        JOIN product_formats pf ON ws.product_format_id = pf.id
        JOIN products p ON pf.product_id = p.id
        JOIN brands b ON p.brand_id = b.id
        JOIN categories c ON p.category_id = c.id
        JOIN ranges r ON p.range_id = r.id
        JOIN websites w ON ws.website_id = w.id
        LEFT JOIN stores s ON ws.store_id = s.id
        LEFT JOIN LATERAL (
            SELECT rate_to_eur
            FROM exchange_rates
            WHERE currency = ws.currency AND date <= ws.week_start
            ORDER BY date DESC LIMIT 1
        ) fx_hist ON TRUE
        WHERE {where_clause}
    )
    SELECT
        week_start,
        ROUND(AVG(price_eur)::NUMERIC, 2) AS avg_price_eur,
        COUNT(*)::int AS sample_count
    FROM base
    GROUP BY week_start
    ORDER BY week_start DESC
    LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    rows = list(reversed(rows))
    for row in rows:
        row["avg_price_eur"] = _to_float(row["avg_price_eur"])

    return rows


def get_forecasts(product: str):
    query = f"""
    SELECT
        af.forecast_date,
        af.predicted_price,
        af.price_low,
        af.price_high,
        af.confidence_level,
        af.training_points,
        CASE
            WHEN hist_meta.span_weeks > 0
                THEN ROUND((hist_meta.observed_weeks::NUMERIC / hist_meta.span_weeks::NUMERIC) * 100, 2)
            ELSE NULL
        END AS coverage_rate,
        hist_meta.last_observed_week,
        CASE
            WHEN s.store_code IS NOT NULL THEN w.site_name || ' (' || s.store_code || ')'
            ELSE w.site_name
        END AS store
    FROM price_forecasts af
    JOIN product_formats pf ON af.product_format_id = pf.id
    JOIN products p ON pf.product_id = p.id
    JOIN brands b ON p.brand_id = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    JOIN websites w ON af.website_id = w.id
    LEFT JOIN stores s ON af.store_id = s.id
    LEFT JOIN LATERAL (
        SELECT
            COUNT(*)::int AS observed_weeks,
            GREATEST(((MAX(ws_hist.week_start) - MIN(ws_hist.week_start)) / 7)::int + 1, 1) AS span_weeks,
            MAX(ws_hist.week_start)::date AS last_observed_week
        FROM weekly_price_summary ws_hist
        WHERE ws_hist.product_format_id = af.product_format_id
          AND ws_hist.website_id = af.website_id
          AND ws_hist.store_id IS NOT DISTINCT FROM af.store_id
    ) hist_meta ON TRUE
    WHERE {PRODUCT_LABEL_SQL} = %s
    ORDER BY af.forecast_date ASC
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (product,))
            rows = cur.fetchall()

    for row in rows:
        row["predicted_price"] = _to_float(row["predicted_price"])
        row["price_low"] = _to_float(row["price_low"])
        row["price_high"] = _to_float(row["price_high"])
        row["coverage_rate"] = _to_float(row.get("coverage_rate"))

    return rows
