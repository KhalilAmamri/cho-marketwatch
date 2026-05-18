from datetime import date, timedelta
from typing import Literal
from psycopg2.extras import RealDictCursor

from app.db.connection import get_connection

PRODUCT_LABEL_SQL = (
    "b.brand_name || ' ' || c.category_name || ' ' || r.range_name || ' ' || f.format_name || ' ' || pk.packaging_name"
)

PRODUCT_FAMILY_SQL = (
    "b.brand_name || ' ' || c.category_name || ' ' || r.range_name"
)

PRODUCT_VARIANT_SQL = "f.format_name || ' ' || pk.packaging_name"

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


def _unit_price_sql(price_sql: str) -> str:
    return f"""
    CASE
        WHEN f.volume_value IS NULL OR f.volume_unit IS NULL THEN NULL
        WHEN f.volume_unit = 'L' AND f.volume_value > 0 THEN ROUND(({price_sql} / f.volume_value)::NUMERIC, 2)
        WHEN f.volume_unit = 'ML' AND f.volume_value > 0 THEN ROUND(({price_sql} * 1000 / f.volume_value)::NUMERIC, 2)
        ELSE NULL
    END
    """

PriceMode = Literal["average", "last_scraped"]


def _to_float(value):
    return float(value) if value is not None else None


def get_kpis():
    query = """
    WITH price_data AS (
        SELECT
            COALESCE(
                MAX(week_start) FILTER (WHERE data_status IN ('OK', 'PARTIAL')),
                MAX(week_start)
            ) AS latest_week_start,
            MAX(updated_at) AS last_refreshed_at,
            COALESCE(
                MAX(week_start) FILTER (WHERE data_status IN ('OK', 'PARTIAL')),
                MAX(week_start)
            )::timestamp AS last_update,
            COUNT(DISTINCT product_variant_id) AS products_tracked,
            COUNT(DISTINCT website_id) AS websites_tracked,
            COUNT(DISTINCT CASE
                WHEN store_id IS NULL THEN 'website:' || website_id::text
                ELSE 'store:' || store_id::text
            END) AS stores_tracked_with_data,
            COUNT(*) FILTER (
                WHERE week_start = COALESCE(
                    (SELECT MAX(week_start) FROM weekly_price_summary WHERE data_status IN ('OK', 'PARTIAL')),
                    (SELECT MAX(week_start) FROM weekly_price_summary)
                )
                AND data_status IN ('OK', 'PARTIAL')
            ) AS latest_week_records
        FROM weekly_price_summary
    ),
    website_store_count AS (
        -- Count explicit stores per website
        SELECT
            w.id AS website_id,
            COUNT(s.id) AS explicit_store_count
        FROM websites w
        LEFT JOIN stores s ON s.website_id = w.id
        GROUP BY w.id
    )
    SELECT
        pd.latest_week_start,
        pd.last_refreshed_at,
        pd.last_update,
        pd.products_tracked,
        pd.websites_tracked,
        -- Total stores = websites without explicit stores (count as 1 default each)
        -- plus websites with explicit stores (count the actual store count)
        COALESCE(
            SUM(CASE WHEN wsc.explicit_store_count = 0 THEN 1 ELSE wsc.explicit_store_count END),
            0
        ) AS stores_tracked,
        pd.latest_week_records
    FROM price_data pd
    CROSS JOIN website_store_count wsc
    GROUP BY
        pd.latest_week_start,
        pd.last_refreshed_at,
        pd.last_update,
        pd.products_tracked,
        pd.websites_tracked,
        pd.latest_week_records
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            row = cur.fetchone()
    return row


def get_filters():
    query = f"""
    SELECT
        pv.id AS product_variant_id,
        {PRODUCT_LABEL_SQL} AS label,
        {PRODUCT_FAMILY_SQL} AS family_label,
        {PRODUCT_VARIANT_SQL} AS variant_label,
        b.brand_name AS brand,
        c.category_name AS category,
        r.range_name,
        f.format_name AS format,
        pk.packaging_name AS packaging
        , f.volume_value,
        f.volume_unit
    FROM product_variants pv
    JOIN products p ON pv.product_id = p.id
    JOIN formats f ON pv.format_id = f.id
    JOIN packagings pk ON pv.packaging_id = pk.id
    JOIN brands b ON p.brand_id = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    ORDER BY b.brand_name, c.category_name, r.range_name, f.format_name, pk.packaging_name
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            products = cur.fetchall()

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


def get_summary(
    week_start: date | None = None,
    fx_basis_week_start: date | None = None,
    all_weeks: bool = False,
    price_mode: PriceMode = "average",
    product_variant_id: int | None = None,
):
    filters = []
    params: list[date | int] = []

    if week_start:
        filters.append("ws.week_start = %s")
        params.append(week_start)
    elif not all_weeks:
        filters.append("""
        ws.week_start = COALESCE(
            (SELECT MAX(week_start) FROM weekly_price_summary WHERE data_status IN ('OK', 'PARTIAL')),
            (SELECT MAX(week_start) FROM weekly_price_summary)
        )
        """)

    if product_variant_id is not None:
        filters.append("ws.product_variant_id = %s")
        params.append(product_variant_id)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    last_scrape_price_eur_sql = """
    CASE
        WHEN last_scrape.price IS NULL THEN NULL
        WHEN COALESCE(NULLIF(BTRIM(last_scrape.currency), ''), ws.currency) = 'EUR'
        THEN ROUND(last_scrape.price::NUMERIC, 2)
        WHEN fx_last.rate_to_eur IS NOT NULL
        THEN ROUND((last_scrape.price / fx_last.rate_to_eur)::NUMERIC, 2)
        ELSE NULL
    END
    """

    if price_mode == "last_scraped":
        query = f"""
    SELECT
        pv.id AS product_variant_id,
        {PRODUCT_LABEL_SQL} AS product,
        {PRODUCT_FAMILY_SQL} AS family_label,
        {PRODUCT_VARIANT_SQL} AS variant_label,
        b.brand_name AS brand,
        c.category_name AS category,
        r.range_name,
        f.format_name AS format,
        pk.packaging_name AS packaging,
        f.volume_value,
        f.volume_unit,
        w.site_name AS website,
        w.country AS country,
        {STORE_LABEL_SQL} AS store,
        COALESCE(NULLIF(BTRIM(last_scrape.currency), ''), ws.currency) AS currency,
        last_scrape.price AS price,
        last_scrape.base_price AS base_price,
        last_scrape.is_discounted AS is_discounted,
        {last_scrape_price_eur_sql} AS price_eur,
        {_unit_price_sql(last_scrape_price_eur_sql)} AS unit_price_eur,
        CASE
            WHEN f.volume_unit IN ('L', 'ML') THEN 'EUR/L'
            ELSE NULL
        END AS unit_label,
        CASE
            WHEN last_scrape.id IS NULL THEN 'MISSING'
            ELSE 'OK'
        END AS data_status,
        source_link.url AS source_url,
        COALESCE(NULLIF(BTRIM(last_scrape.screenshot_path), ''), latest_shot.screenshot_path) AS screenshot_path,
        ws.week_start
    FROM weekly_price_summary ws
    JOIN product_variants pv ON ws.product_variant_id = pv.id
    JOIN products p ON pv.product_id = p.id
    JOIN formats f ON pv.format_id = f.id
    JOIN packagings pk ON pv.packaging_id = pk.id
    JOIN brands b ON p.brand_id = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    JOIN websites w ON ws.website_id = w.id
    LEFT JOIN stores s ON ws.store_id = s.id
    LEFT JOIN LATERAL (
        SELECT pu.url
        FROM product_urls pu
        WHERE pu.website_id = ws.website_id
            AND pu.product_variant_id = ws.product_variant_id
            AND pu.store_id IS NOT DISTINCT FROM ws.store_id
            AND pu.url IS NOT NULL
            AND BTRIM(pu.url) <> ''
        ORDER BY pu.is_active DESC, pu.created_at DESC, pu.id DESC
        LIMIT 1
    ) source_link ON TRUE
    LEFT JOIN LATERAL (
                SELECT
                        sp.id,
                        sp.current_price AS price,
                        sp.base_price,
                        sp.is_discounted,
                        sp.currency,
                        sp.screenshot_path,
                        sp.observed_at
        FROM scraped_prices sp
        WHERE sp.product_variant_id = ws.product_variant_id
          AND sp.website_id = ws.website_id
          AND sp.store_id IS NOT DISTINCT FROM ws.store_id
          AND date_trunc('week', sp.observed_at)::date = ws.week_start
        ORDER BY sp.observed_at DESC, sp.id DESC
        LIMIT 1
    ) last_scrape ON TRUE
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = COALESCE(NULLIF(BTRIM(last_scrape.currency), ''), ws.currency)
          AND date <= last_scrape.observed_at::date
        ORDER BY date DESC
        LIMIT 1
    ) fx_last ON TRUE
    LEFT JOIN LATERAL (
        SELECT sp.screenshot_path
        FROM scraped_prices sp
        WHERE sp.product_variant_id = ws.product_variant_id
          AND sp.website_id = ws.website_id
          AND sp.store_id IS NOT DISTINCT FROM ws.store_id
          AND date_trunc('week', sp.observed_at)::date = ws.week_start
          AND sp.screenshot_path IS NOT NULL
          AND BTRIM(sp.screenshot_path) <> ''
        ORDER BY sp.observed_at DESC, sp.id DESC
        LIMIT 1
    ) latest_shot ON TRUE
    {where_clause}
    ORDER BY ws.week_start DESC, product, website, store
    """
    elif price_mode == "average":
        fx_hist_join = """
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = ws.currency AND date <= ws.week_start
        ORDER BY date DESC LIMIT 1
    ) fx_hist ON TRUE
    """

        params_for_query = list(params)
        if fx_basis_week_start is not None:
            fx_hist_join = """
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = ws.currency AND date <= %s
        ORDER BY date DESC LIMIT 1
    ) fx_hist ON TRUE
    """
            # The FX basis placeholder appears before any WHERE placeholders.
            params_for_query = [fx_basis_week_start, *params_for_query]

        query = f"""
    SELECT
        pv.id AS product_variant_id,
        {PRODUCT_LABEL_SQL} AS product,
        {PRODUCT_FAMILY_SQL} AS family_label,
        {PRODUCT_VARIANT_SQL} AS variant_label,
        b.brand_name AS brand,
        c.category_name AS category,
        r.range_name,
        f.format_name AS format,
        pk.packaging_name AS packaging,
        f.volume_value,
        f.volume_unit,
        w.site_name AS website,
        w.country AS country,
        {STORE_LABEL_SQL} AS store,
        ws.currency,
        ws.avg_price AS price,
        {PRICE_EUR_SQL} AS price_eur,
        {_unit_price_sql(PRICE_EUR_SQL)} AS unit_price_eur,
        CASE
            WHEN f.volume_unit IN ('L', 'ML') THEN 'EUR/L'
            ELSE NULL
        END AS unit_label,
        ws.data_status,
        source_link.url AS source_url,
        latest_shot.screenshot_path AS screenshot_path,
        ws.week_start
    FROM weekly_price_summary ws
    JOIN product_variants pv ON ws.product_variant_id = pv.id
    JOIN products p ON pv.product_id = p.id
    JOIN formats f ON pv.format_id = f.id
    JOIN packagings pk ON pv.packaging_id = pk.id
    JOIN brands b ON p.brand_id = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    JOIN websites w ON ws.website_id = w.id
    LEFT JOIN stores s ON ws.store_id = s.id
    LEFT JOIN LATERAL (
        SELECT pu.url
        FROM product_urls pu
        WHERE pu.website_id = ws.website_id
            AND pu.product_variant_id = ws.product_variant_id
            AND pu.store_id IS NOT DISTINCT FROM ws.store_id
            AND pu.url IS NOT NULL
            AND BTRIM(pu.url) <> ''
        ORDER BY pu.is_active DESC, pu.created_at DESC, pu.id DESC
        LIMIT 1
    ) source_link ON TRUE
    {fx_hist_join}
    LEFT JOIN LATERAL (
        SELECT sp.screenshot_path
        FROM scraped_prices sp
        WHERE sp.product_variant_id = ws.product_variant_id
          AND sp.website_id = ws.website_id
          AND sp.store_id IS NOT DISTINCT FROM ws.store_id
          AND date_trunc('week', sp.observed_at)::date = ws.week_start
          AND sp.screenshot_path IS NOT NULL
          AND BTRIM(sp.screenshot_path) <> ''
        ORDER BY sp.observed_at DESC, sp.id DESC
        LIMIT 1
    ) latest_shot ON TRUE
    {where_clause}
    ORDER BY ws.week_start DESC, product, website, store
    """
    else:
        raise ValueError(f"Unsupported price_mode: {price_mode}")

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params_for_query if price_mode == "average" else params)
            rows = cur.fetchall()

    for row in rows:
        row["price"] = _to_float(row["price"])
        row["base_price"] = _to_float(row.get("base_price"))
        row["price_eur"] = _to_float(row["price_eur"])
        row["unit_price_eur"] = _to_float(row.get("unit_price_eur"))

    return rows


def get_timeseries(
    product_variant_id: int,
    website: str | None = None,
    country: str | None = None,
    weeks: int = 52,
    store: str | None = None,
    fx_basis_week_start: date | None = None,
):
    filters = ["ws.product_variant_id = %s"]
    params = [product_variant_id]

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
    effective_weeks = None if weeks == 0 else weeks
    if effective_weeks is not None:
        params.append(effective_weeks)

    limit_clause = "LIMIT %s" if effective_weeks is not None else ""

    fx_hist_join = """
        LEFT JOIN LATERAL (
            SELECT rate_to_eur
            FROM exchange_rates
            WHERE currency = ws.currency AND date <= ws.week_start
            ORDER BY date DESC LIMIT 1
        ) fx_hist ON TRUE
    """

    params_for_query = list(params)
    if fx_basis_week_start is not None:
        fx_hist_join = """
        LEFT JOIN LATERAL (
            SELECT rate_to_eur
            FROM exchange_rates
            WHERE currency = ws.currency AND date <= %s
            ORDER BY date DESC LIMIT 1
        ) fx_hist ON TRUE
    """
        # The FX basis placeholder appears before any WHERE placeholders.
        params_for_query = [fx_basis_week_start, *params_for_query]

    query = f"""
    WITH base AS (
        SELECT
            ws.week_start,
            ws.data_status,
            {PRICE_EUR_SQL} AS price_eur,
            {_unit_price_sql(PRICE_EUR_SQL)} AS unit_price_eur,
            CASE
                WHEN f.volume_unit IN ('L', 'ML') THEN 'EUR/L'
                ELSE NULL
            END AS unit_label
        FROM weekly_price_summary ws
        JOIN product_variants pv ON ws.product_variant_id = pv.id
        JOIN formats f ON pv.format_id = f.id
        JOIN websites w ON ws.website_id = w.id
        LEFT JOIN stores s ON ws.store_id = s.id
        {fx_hist_join}
        WHERE {where_clause}
    )
    SELECT
        week_start,
        CASE
            WHEN BOOL_OR(data_status IN ('OK', 'PARTIAL') AND price_eur IS NOT NULL)
            THEN ROUND(AVG(price_eur) FILTER (WHERE data_status IN ('OK', 'PARTIAL') AND price_eur IS NOT NULL)::NUMERIC, 2)
            ELSE NULL
        END AS avg_price_eur,
        CASE
            WHEN BOOL_OR(data_status IN ('OK', 'PARTIAL') AND unit_price_eur IS NOT NULL)
            THEN ROUND(AVG(unit_price_eur) FILTER (WHERE data_status IN ('OK', 'PARTIAL') AND unit_price_eur IS NOT NULL)::NUMERIC, 2)
            ELSE NULL
        END AS avg_unit_price_eur,
        MAX(unit_label) AS unit_label,
        COUNT(*) FILTER (WHERE data_status IN ('OK', 'PARTIAL') AND price_eur IS NOT NULL)::int AS sample_count,
        CASE
            WHEN BOOL_OR(data_status IN ('OK', 'PARTIAL') AND price_eur IS NOT NULL)
                 AND BOOL_OR(data_status = 'MISSING')
            THEN 'PARTIAL'
            WHEN BOOL_OR(data_status IN ('OK', 'PARTIAL') AND price_eur IS NOT NULL)
            THEN 'OK'
            ELSE 'MISSING'
        END AS data_status
    FROM base
    GROUP BY week_start
    ORDER BY week_start DESC
    {limit_clause}
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params_for_query)
            rows = cur.fetchall()

    rows = list(reversed(rows))
    for row in rows:
        row["avg_price_eur"] = _to_float(row["avg_price_eur"])
        row["avg_unit_price_eur"] = _to_float(row["avg_unit_price_eur"])

    return rows


def get_price_analysis(
    product_variant_ids: list[int] | None = None,
    website: str | None = None,
    country: str | None = None,
    weeks: int = 52,
    fx_basis_week_start: date | None = None,
):
    """Return compact dashboard datasets for Price Analytics.

    All price KPIs are computed on unit_price_eur (EUR/L) when available.
    """

    ids = [int(x) for x in (product_variant_ids or []) if int(x) > 0]

    filters: list[str] = []
    params: list[object] = []

    if ids:
        filters.append("ws.product_variant_id = ANY(%s)")
        params.append(ids)

    if website:
        filters.append("w.site_name = %s")
        params.append(website)

    if country:
        filters.append("w.country = %s")
        params.append(country)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    latest_week_query = f"""
    SELECT
        COALESCE(
            MAX(ws.week_start) FILTER (WHERE ws.data_status IN ('OK', 'PARTIAL')),
            MAX(ws.week_start)
        ) AS latest_week_start
    FROM weekly_price_summary ws
    JOIN websites w ON ws.website_id = w.id
    {where_clause}
    """

    fx_hist_join = """
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = ws.currency AND date <= ws.week_start
        ORDER BY date DESC
        LIMIT 1
    ) fx_hist ON TRUE
    """

    params_with_fx = list(params)
    if fx_basis_week_start is not None:
        fx_hist_join = """
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = ws.currency AND date <= %s
        ORDER BY date DESC
        LIMIT 1
    ) fx_hist ON TRUE
    """
        # The FX basis placeholder appears before any WHERE placeholders.
        params_with_fx = [fx_basis_week_start, *params_with_fx]

    base_select = f"""
    SELECT
        ws.product_variant_id,
        {PRODUCT_LABEL_SQL} AS product,
        w.country AS country,
        {STORE_LABEL_SQL} AS store,
        ws.week_start,
        ws.data_status,
        {PRICE_EUR_SQL} AS price_eur,
        {_unit_price_sql(PRICE_EUR_SQL)} AS unit_price_eur,
        CASE
            WHEN f.volume_unit IN ('L', 'ML') THEN 'EUR/L'
            ELSE NULL
        END AS unit_label
    FROM weekly_price_summary ws
    JOIN product_variants pv ON ws.product_variant_id = pv.id
    JOIN products p ON pv.product_id = p.id
    JOIN formats f ON pv.format_id = f.id
    JOIN packagings pk ON pv.packaging_id = pk.id
    JOIN brands b ON p.brand_id = b.id
    JOIN categories c ON p.category_id = c.id
    JOIN ranges r ON p.range_id = r.id
    JOIN websites w ON ws.website_id = w.id
    LEFT JOIN stores s ON ws.store_id = s.id
    {fx_hist_join}
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(latest_week_query, params)
            latest_week_row = cur.fetchone() or {}
            latest_week_start = latest_week_row.get("latest_week_start")

            if latest_week_start is None:
                return {
                    "kpis": {
                        "latest_week_start": None,
                        "products": 0,
                        "stores": 0,
                        "countries": 0,
                        "avg_price_eur": None,
                        "max_price_eur": None,
                        "min_price_eur": None,
                        "unit_label": None,
                    },
                    "clustered": [],
                    "trend": [],
                    "store_share": [],
                }

            # Latest-week base rows
            latest_filters = list(filters)
            latest_params = list(params)
            latest_filters.append("ws.week_start = %s")
            latest_params.append(latest_week_start)
            latest_where = f"WHERE {' AND '.join(latest_filters)}" if latest_filters else ""

            latest_rows_query = f"""
            {base_select}
            {latest_where}
            """
            latest_rows_params = list(latest_params)
            if fx_basis_week_start is not None:
                latest_rows_params = [fx_basis_week_start, *latest_rows_params]

            cur.execute(latest_rows_query, latest_rows_params)
            latest_rows = cur.fetchall()

            # KPIs
            kpi_rows = [
                r
                for r in latest_rows
                if r.get("data_status") in ("OK", "PARTIAL")
                and r.get("price_eur") is not None
            ]
            values = [float(r["price_eur"]) for r in kpi_rows]

            products = len({r["product_variant_id"] for r in kpi_rows})
            stores = len({r["store"] for r in kpi_rows})
            countries_count = len({r.get("country") for r in kpi_rows if r.get("country")})

            avg_value = round(sum(values) / len(values), 2) if values else None
            max_value = round(max(values), 2) if values else None
            min_value = round(min(values), 2) if values else None
            unit_label = "EUR"

            # Clustered bar (ranked by price within each product)
            by_product: dict[int, dict[str, object]] = {}
            for row in kpi_rows:
                pid = int(row["product_variant_id"])
                entry = by_product.get(pid)
                if entry is None:
                    entry = {"product": row["product"], "stores": []}
                    by_product[pid] = entry
                entry["stores"].append(
                    {
                        "store": row["store"],
                        "country": row.get("country"),
                        "unit_price_eur": float(row["unit_price_eur"]),
                        "price_eur": _to_float(row.get("price_eur")),
                    }
                )

            clustered = []
            for pid, payload in by_product.items():
                stores_list = payload["stores"]
                stores_list = sorted(stores_list, key=lambda x: x["unit_price_eur"])
                ranks = [
                    {
                        "rank": index + 1,
                        "store": item["store"],
                        "country": item.get("country"),
                        "unit_price_eur": round(float(item["unit_price_eur"]), 2),
                        "price_eur": round(float(item["price_eur"]), 2) if item.get("price_eur") is not None else None,
                    }
                    for index, item in enumerate(stores_list)
                ]
                clustered.append(
                    {
                        "product_variant_id": pid,
                        "product": payload["product"],
                        "ranks": ranks,
                    }
                )
            clustered.sort(key=lambda x: x["product"].lower())

            # Store share (latest week)
            share: dict[str, tuple[int, str | None]] = {}
            for row in kpi_rows:
                store_key = row["store"]
                if store_key not in share:
                    share[store_key] = (0, row.get("country"))
                count, country = share[store_key]
                share[store_key] = (count + 1, country)
            
            store_share = [
                {"store": store, "country": country, "records": count}
                for store, (count, country) in sorted(share.items(), key=lambda x: (-x[1][0], x[0].lower()))
            ]

            # Trend (weekly) - get last N weeks for filtered products
            trend_params = list(params)
            trend_params.append(weeks)

            trend_params_with_fx = list(trend_params)
            if fx_basis_week_start is not None:
                trend_params_with_fx = [fx_basis_week_start, *trend_params_with_fx]
            
            trend_query = f"""
            SELECT
                ws.week_start,
                CASE
                    WHEN BOOL_OR(ws.data_status IN ('OK', 'PARTIAL') AND {PRICE_EUR_SQL} IS NOT NULL)
                    THEN ROUND(
                        AVG({PRICE_EUR_SQL}) FILTER (WHERE ws.data_status IN ('OK', 'PARTIAL') AND {PRICE_EUR_SQL} IS NOT NULL)::NUMERIC,
                        2
                    )
                    ELSE NULL
                END AS avg_price_eur,
                CASE
                    WHEN BOOL_OR(ws.data_status IN ('OK', 'PARTIAL') AND {_unit_price_sql(PRICE_EUR_SQL)} IS NOT NULL)
                    THEN ROUND(
                        AVG({_unit_price_sql(PRICE_EUR_SQL)}) FILTER (WHERE ws.data_status IN ('OK', 'PARTIAL') AND {_unit_price_sql(PRICE_EUR_SQL)} IS NOT NULL)::NUMERIC,
                        2
                    )
                    ELSE NULL
                END AS avg_unit_price_eur,
                MAX(
                    CASE
                        WHEN f.volume_unit IN ('L', 'ML') THEN 'EUR/L'
                        ELSE NULL
                    END
                ) AS unit_label,
                COUNT(*) FILTER (WHERE ws.data_status IN ('OK', 'PARTIAL') AND {_unit_price_sql(PRICE_EUR_SQL)} IS NOT NULL)::int AS sample_count,
                CASE
                    WHEN BOOL_OR(ws.data_status IN ('OK', 'PARTIAL') AND {_unit_price_sql(PRICE_EUR_SQL)} IS NOT NULL)
                         AND BOOL_OR(ws.data_status = 'MISSING')
                    THEN 'PARTIAL'
                    WHEN BOOL_OR(ws.data_status IN ('OK', 'PARTIAL') AND {_unit_price_sql(PRICE_EUR_SQL)} IS NOT NULL)
                    THEN 'OK'
                    ELSE 'MISSING'
                END AS data_status
            FROM weekly_price_summary ws
            JOIN websites w ON ws.website_id = w.id
            JOIN product_variants pv ON ws.product_variant_id = pv.id
            JOIN formats f ON pv.format_id = f.id
            {fx_hist_join}
            WHERE 1=1
            {(' AND ' + ' AND '.join(filters)) if filters else ''}
            GROUP BY ws.week_start
            ORDER BY ws.week_start DESC
            LIMIT %s
            """

            cur.execute(trend_query, trend_params_with_fx)
            trend_rows = cur.fetchall()
            for row in trend_rows:
                row["avg_price_eur"] = _to_float(row.get("avg_price_eur"))
                row["avg_unit_price_eur"] = _to_float(row.get("avg_unit_price_eur"))

            return {
                "kpis": {
                    "latest_week_start": latest_week_start,
                    "products": products,
                    "stores": stores,
                    "countries": countries_count,
                    "avg_price_eur": avg_value,
                    "max_price_eur": max_value,
                    "min_price_eur": min_value,
                    "unit_label": unit_label,
                },
                "clustered": clustered,
                "trend": trend_rows,
                "store_share": store_share,
            }


def get_market_overview(
    website: str | None = None,
    country: str | None = None,
    store: str | None = None,
    week_start: date | None = None,
    fx_basis_week_start: date | None = None,
):
    """Return latest-week market overview aggregated by store.

    KPIs and rankings are computed on unit_price_eur (EUR/L) when available.
    """

    filters: list[str] = []
    params: list[object] = []

    if website:
        filters.append("w.site_name = %s")
        params.append(website)

    if country:
        filters.append("w.country = %s")
        params.append(country)

    if store:
        filters.append(f"({STORE_LABEL_SQL}) = %s")
        params.append(store)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    latest_week_query = f"""
    SELECT
        COALESCE(
            MAX(ws.week_start) FILTER (WHERE ws.data_status IN ('OK', 'PARTIAL')),
            MAX(ws.week_start)
        ) AS latest_week_start
    FROM weekly_price_summary ws
    JOIN websites w ON ws.website_id = w.id
    LEFT JOIN stores s ON ws.store_id = s.id
    {where_clause}
    """

    fx_hist_join = """
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = ws.currency AND date <= ws.week_start
        ORDER BY date DESC
        LIMIT 1
    ) fx_hist ON TRUE
    """

    base_select = f"""
    SELECT
        ws.product_variant_id,
        w.country AS country,
        {STORE_LABEL_SQL} AS store,
        ws.week_start,
        ws.data_status,
        {PRICE_EUR_SQL} AS price_eur,
        {_unit_price_sql(PRICE_EUR_SQL)} AS unit_price_eur
    FROM weekly_price_summary ws
    JOIN product_variants pv ON ws.product_variant_id = pv.id
    JOIN formats f ON pv.format_id = f.id
    JOIN websites w ON ws.website_id = w.id
    LEFT JOIN stores s ON ws.store_id = s.id
    {fx_hist_join}
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if week_start is not None:
                latest_week_start = week_start
            else:
                cur.execute(latest_week_query, params)
                latest_week_row = cur.fetchone() or {}
                latest_week_start = latest_week_row.get("latest_week_start")

            if latest_week_start is None:
                return {
                    "kpis": {
                        "latest_week_start": None,
                        "products": 0,
                        "stores": 0,
                        "countries": 0,
                        "avg_discount_pct": None,
                        "avg_unit_price_eur": None,
                        "max_unit_price_eur": None,
                        "min_unit_price_eur": None,
                        "unit_label": None,
                    },
                    "store_rankings": [],
                    "store_presence": [],
                }

            latest_filters = list(filters)
            latest_params = list(params)
            latest_filters.append("ws.week_start = %s")
            latest_params.append(latest_week_start)
            latest_where = f"WHERE {' AND '.join(latest_filters)}" if latest_filters else ""

            latest_rows_query = f"""
            {base_select}
            {latest_where}
            """
            latest_rows_params = list(latest_params)
            if fx_basis_week_start is not None:
                base_select = base_select.replace(
                    "WHERE currency = ws.currency AND date <= ws.week_start",
                    "WHERE currency = ws.currency AND date <= %s",
                )
                latest_rows_query = f"""
                {base_select}
                {latest_where}
                """
                # FX basis placeholder appears before any WHERE placeholders.
                latest_rows_params = [fx_basis_week_start, *latest_rows_params]

            cur.execute(latest_rows_query, latest_rows_params)
            latest_rows = cur.fetchall()

            if not latest_rows:
                return {
                    "kpis": {
                        "latest_week_start": latest_week_start,
                        "products": 0,
                        "stores": 0,
                        "countries": 0,
                        "avg_discount_pct": None,
                        "avg_unit_price_eur": None,
                        "max_unit_price_eur": None,
                        "min_unit_price_eur": None,
                        "unit_label": None,
                    },
                    "store_rankings": [],
                    "store_presence": [],
                }

            # Avg discount (%), computed from scraped_prices for the selected week.
            discount_where = "WHERE date_trunc('week', sp.observed_at)::date = %s"
            if filters:
                discount_where += " AND " + " AND ".join(filters)

            discount_query = f"""
            SELECT
                AVG((sp.base_price - sp.current_price) / NULLIF(sp.base_price, 0)) AS avg_discount_frac
            FROM scraped_prices sp
            JOIN websites w ON sp.website_id = w.id
            LEFT JOIN stores s ON sp.store_id = s.id
            {discount_where}
              AND sp.base_price IS NOT NULL
              AND sp.current_price IS NOT NULL
              AND sp.base_price > sp.current_price
            """

            discount_params = [latest_week_start, *params]
            cur.execute(discount_query, discount_params)
            discount_row = cur.fetchone() or {}
            avg_discount_frac = discount_row.get("avg_discount_frac")
            avg_discount_pct = round(float(avg_discount_frac) * 100, 1) if avg_discount_frac is not None else None

            usable_rows = [
                r
                for r in latest_rows
                if r.get("data_status") in ("OK", "PARTIAL") and r.get("unit_price_eur") is not None
            ]

            unit_values = [float(r["unit_price_eur"]) for r in usable_rows]
            products = len({r["product_variant_id"] for r in usable_rows})
            stores_count = len({r["store"] for r in usable_rows})
            countries_count = len({r.get("country") for r in usable_rows if r.get("country")})

            avg_value = round(sum(unit_values) / len(unit_values), 2) if unit_values else None
            max_value = round(max(unit_values), 2) if unit_values else None
            min_value = round(min(unit_values), 2) if unit_values else None

            # Rankings (avg unit price per store)
            by_store: dict[str, dict[str, object]] = {}
            for row in usable_rows:
                store_key = row["store"]
                entry = by_store.get(store_key)
                if entry is None:
                    entry = {"country": row.get("country"), "values": []}
                    by_store[store_key] = entry
                entry["values"].append(float(row["unit_price_eur"]))

            store_rankings = []
            for store_key, payload in by_store.items():
                values = payload["values"]
                avg_store = round(sum(values) / len(values), 2) if values else None
                store_rankings.append(
                    {
                        "store": store_key,
                        "country": payload.get("country"),
                        "avg_unit_price_eur": avg_store,
                        "sample_count": len(values),
                    }
                )
            store_rankings.sort(
                key=lambda x: (x["avg_unit_price_eur"] is None, x["avg_unit_price_eur"] or 0, x["store"].lower())
            )

            # Presence (records per store)
            presence = []
            for store_key, payload in sorted(
                ((k, v) for k, v in by_store.items()),
                key=lambda x: (-len(x[1]["values"]), x[0].lower()),
            ):
                presence.append(
                    {
                        "store": store_key,
                        "country": payload.get("country"),
                        "records": len(payload["values"]),
                    }
                )

            return {
                "kpis": {
                    "latest_week_start": latest_week_start,
                    "products": products,
                    "stores": stores_count,
                    "countries": countries_count,
                    "avg_discount_pct": avg_discount_pct,
                    "avg_unit_price_eur": avg_value,
                    "max_unit_price_eur": max_value,
                    "min_unit_price_eur": min_value,
                    "unit_label": "EUR/L" if unit_values else None,
                },
                "store_rankings": store_rankings,
                "store_presence": presence,
            }


def get_market_changes(
    week_start: date,
    previous_week_start: date | None = None,
    fx_basis_week_start: date | None = None,
    website: str | None = None,
    country: str | None = None,
    store: str | None = None,
    limit: int = 15,
):
    """Return products whose unit price (EUR/L) changed WoW.

    Important: the Market Context Avg KPI is computed over store-level rows
    (product × website × store). To explain that movement, we detect changes
    at the same granularity and then pick the biggest store-level change per
    product.
    """

    if previous_week_start is None:
        previous_week_start = week_start - timedelta(days=7)

    filters: list[str] = []
    params: list[object] = []

    if website:
        filters.append("w.site_name = %s")
        params.append(website)

    if country:
        filters.append("w.country = %s")
        params.append(country)

    if store:
        filters.append(f"({STORE_LABEL_SQL}) = %s")
        params.append(store)

    where_tail = (" AND " + " AND ".join(filters)) if filters else ""

    fx_date_expr = "%s" if fx_basis_week_start else "ws.week_start"
    fx_hist_join = f"""
    LEFT JOIN LATERAL (
        SELECT rate_to_eur
        FROM exchange_rates
        WHERE currency = ws.currency
          AND date <= {fx_date_expr}
        ORDER BY date DESC
        LIMIT 1
    ) fx_hist ON TRUE
    """

    unit_price_eur_sql = _unit_price_sql(PRICE_EUR_SQL)
    query = f"""
    WITH current_rows AS (
        SELECT
            ws.product_variant_id,
            ws.website_id,
            ws.store_id,
            ({unit_price_eur_sql})::NUMERIC AS unit_price_eur
        FROM weekly_price_summary ws
        JOIN websites w ON ws.website_id = w.id
        LEFT JOIN stores s ON ws.store_id = s.id
        JOIN product_variants pv ON ws.product_variant_id = pv.id
        JOIN formats f ON pv.format_id = f.id
        {fx_hist_join}
        WHERE ws.week_start = %s
          AND ws.currency IS NOT NULL
          AND ws.data_status IN ('OK', 'PARTIAL')
          AND ({unit_price_eur_sql}) IS NOT NULL
          {where_tail}
    ),
    previous_rows AS (
        SELECT
            ws.product_variant_id,
            ws.website_id,
            ws.store_id,
            ({unit_price_eur_sql})::NUMERIC AS unit_price_eur
        FROM weekly_price_summary ws
        JOIN websites w ON ws.website_id = w.id
        LEFT JOIN stores s ON ws.store_id = s.id
        JOIN product_variants pv ON ws.product_variant_id = pv.id
        JOIN formats f ON pv.format_id = f.id
        {fx_hist_join}
        WHERE ws.week_start = %s
          AND ws.currency IS NOT NULL
          AND ws.data_status IN ('OK', 'PARTIAL')
          AND ({unit_price_eur_sql}) IS NOT NULL
          {where_tail}
    ),
    changed_rows AS (
        SELECT
            c.product_variant_id,
            c.website_id,
            c.store_id,
            c.unit_price_eur AS this_week_unit_price_eur,
            p.unit_price_eur AS last_week_unit_price_eur,
            (c.unit_price_eur - p.unit_price_eur) AS delta_unit_price_eur,
            CASE
                WHEN p.unit_price_eur IS NULL OR p.unit_price_eur = 0 THEN NULL
                ELSE ((c.unit_price_eur - p.unit_price_eur) / p.unit_price_eur) * 100
            END AS delta_pct
        FROM current_rows c
        JOIN previous_rows p
          ON p.product_variant_id = c.product_variant_id
         AND p.website_id = c.website_id
         AND (p.store_id IS NOT DISTINCT FROM c.store_id)
        WHERE c.unit_price_eur IS NOT NULL
          AND p.unit_price_eur IS NOT NULL
          AND c.unit_price_eur <> p.unit_price_eur
    ),
    ranked AS (
        SELECT
            cr.*,
            ROW_NUMBER() OVER (
                PARTITION BY cr.product_variant_id
                ORDER BY ABS(cr.delta_pct) DESC NULLS LAST, ABS(cr.delta_unit_price_eur) DESC NULLS LAST
            ) AS rn
        FROM changed_rows cr
    )
    SELECT
        m.product_variant_id,
        {PRODUCT_LABEL_SQL} AS product,
        m.this_week_unit_price_eur,
        m.last_week_unit_price_eur,
        m.delta_unit_price_eur,
        m.delta_pct,
        COALESCE(disc.has_discount, FALSE) AS has_discount,
        ex.screenshot_path,
        ex.source_url,
        ex.example_store,
        ex.example_country
    FROM ranked m
    JOIN product_variants pv ON pv.id = m.product_variant_id
    JOIN products p ON pv.product_id = p.id
    JOIN formats f ON pv.format_id = f.id
    JOIN packagings pk ON pv.packaging_id = pk.id
    LEFT JOIN brands b ON p.brand_id = b.id
    LEFT JOIN categories c ON p.category_id = c.id
    LEFT JOIN ranges r ON p.range_id = r.id
    LEFT JOIN LATERAL (
        SELECT
            sp.screenshot_path,
            pu.url AS source_url,
            ({STORE_LABEL_SQL}) AS example_store,
            w.country AS example_country
        FROM scraped_prices sp
        JOIN websites w ON sp.website_id = w.id
        LEFT JOIN stores s ON sp.store_id = s.id
        LEFT JOIN LATERAL (
            SELECT url
            FROM product_urls pu
            WHERE pu.website_id = sp.website_id
              AND pu.product_variant_id = sp.product_variant_id
              AND (pu.store_id IS NOT DISTINCT FROM sp.store_id)
            ORDER BY pu.is_active DESC, pu.created_at DESC, pu.id DESC
            LIMIT 1
        ) pu ON TRUE
        WHERE sp.product_variant_id = m.product_variant_id
          AND sp.website_id = m.website_id
          AND (sp.store_id IS NOT DISTINCT FROM m.store_id)
          AND sp.observed_at >= %s::date
          AND sp.observed_at < (%s::date + INTERVAL '7 days')
        ORDER BY (sp.is_discounted IS TRUE) DESC, sp.observed_at DESC, sp.id DESC
        LIMIT 1
    ) ex ON TRUE
    LEFT JOIN LATERAL (
        SELECT EXISTS (
            SELECT 1
            FROM scraped_prices sp
            WHERE sp.product_variant_id = m.product_variant_id
              AND sp.website_id = m.website_id
              AND (sp.store_id IS NOT DISTINCT FROM m.store_id)
              AND sp.observed_at >= %s::date
              AND sp.observed_at < (%s::date + INTERVAL '7 days')
              AND sp.is_discounted = TRUE
        ) AS has_discount
    ) disc ON TRUE
    WHERE m.rn = 1
    ORDER BY ABS(m.delta_pct) DESC NULLS LAST, ABS(m.delta_unit_price_eur) DESC NULLS LAST, product
    LIMIT %s
    """

    query_params: list[object] = []
    if fx_basis_week_start:
        query_params.append(fx_basis_week_start)
    query_params.append(week_start)
    query_params.extend(params)
    if fx_basis_week_start:
        query_params.append(fx_basis_week_start)
    query_params.append(previous_week_start)
    query_params.extend(params)

    # screenshot-week window (ex + has_discount)
    query_params.append(week_start)
    query_params.append(week_start)
    query_params.append(week_start)
    query_params.append(week_start)

    query_params.append(limit)

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, query_params)
            rows = cur.fetchall()

    # Normalize numeric types for JSON
    normalized = []
    for row in rows:
        normalized.append(
            {
                **row,
                "this_week_unit_price_eur": float(row["this_week_unit_price_eur"]) if row.get("this_week_unit_price_eur") is not None else None,
                "last_week_unit_price_eur": float(row["last_week_unit_price_eur"]) if row.get("last_week_unit_price_eur") is not None else None,
                "delta_unit_price_eur": float(row["delta_unit_price_eur"]) if row.get("delta_unit_price_eur") is not None else None,
                "delta_pct": float(row["delta_pct"]) if row.get("delta_pct") is not None else None,
                "has_discount": bool(row.get("has_discount")),
            }
        )

    return normalized


def get_available_weeks(
    website: str | None = None,
    country: str | None = None,
    store: str | None = None,
    limit: int = 260,
):
    filters: list[str] = []
    params: list[object] = []

    if website:
        filters.append("w.site_name = %s")
        params.append(website)

    if country:
        filters.append("w.country = %s")
        params.append(country)

    if store:
        filters.append(f"({STORE_LABEL_SQL}) = %s")
        params.append(store)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = f"""
    SELECT DISTINCT ws.week_start
    FROM weekly_price_summary ws
    JOIN websites w ON ws.website_id = w.id
    LEFT JOIN stores s ON ws.store_id = s.id
    {where_clause}
    ORDER BY ws.week_start DESC
    LIMIT %s
    """
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    return [r[0] for r in rows]


def get_store_universe(
    website: str | None = None,
    country: str | None = None,
):
    """Return the full set of known stores (and website-level retailers).

    For websites that have store branches, returns one entry per store_code (e.g. "Ica (1003425)").
    For websites without stores, returns the website name (e.g. "Citygross").
    """

    filters: list[str] = []
    params: list[object] = []

    if website:
        filters.append("w.site_name = %s")
        params.append(website)

    if country:
        filters.append("w.country = %s")
        params.append(country)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = f"""
    SELECT DISTINCT
        CASE
            WHEN s.id IS NOT NULL THEN w.site_name || ' (' || s.store_code || ')'
            ELSE w.site_name
        END AS store,
        w.country AS country
    FROM websites w
    LEFT JOIN stores s ON s.website_id = w.id
    {where_clause}
    ORDER BY store
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()
