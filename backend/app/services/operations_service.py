from psycopg2.extras import RealDictCursor

from app.db.connection import get_connection


STORE_NAME_SQL = """
CASE
    WHEN s.store_name IS NOT NULL AND BTRIM(s.store_name) <> '' THEN s.store_name
    WHEN s.store_code IS NOT NULL THEN w.site_name || ' (' || s.store_code || ')'
    ELSE w.site_name
END
"""


def get_operational_visibility(limit_failed: int = 100) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)::int AS total_records,
                    COUNT(*) FILTER (WHERE status = 'failed')::int AS failed_requests,
                    COUNT(*) FILTER (
                        WHERE http_status_code BETWEEN 200 AND 299
                          AND status <> 'failed'
                    )::int AS success_requests,
                    COUNT(*) FILTER (WHERE http_status_code = 200)::int AS status_200,
                    COUNT(*) FILTER (WHERE http_status_code = 404)::int AS status_404,
                    COUNT(*) FILTER (WHERE http_status_code = 500)::int AS status_500
                FROM raw_staging
                """
            )
            summary = cur.fetchone() or {}

            cur.execute(
                f"""
                SELECT
                    rs.id,
                    {STORE_NAME_SQL} AS store_name,
                    rs.error_message,
                    rs.screenshot_path,
                    rs.http_status_code,
                    rs.scraped_at
                FROM raw_staging rs
                JOIN product_urls pu ON rs.product_url_id = pu.id
                JOIN websites w ON pu.website_id = w.id
                LEFT JOIN stores s ON pu.store_id = s.id
                WHERE rs.status = 'failed'
                ORDER BY rs.scraped_at DESC
                LIMIT %s
                """,
                (limit_failed,),
            )
            failed_rows = cur.fetchall()

    total_records = int(summary.get("total_records", 0) or 0)
    failed_requests = int(summary.get("failed_requests", 0) or 0)
    success_requests = int(summary.get("success_requests", 0) or 0)
    success_rate = round((success_requests / total_records) * 100, 2) if total_records else 0.0

    status_code_counts = [
        {"status_code": 200, "count": int(summary.get("status_200", 0) or 0)},
        {"status_code": 404, "count": int(summary.get("status_404", 0) or 0)},
        {"status_code": 500, "count": int(summary.get("status_500", 0) or 0)},
    ]

    return {
        "success_rate": success_rate,
        "total_records": total_records,
        "failed_requests": failed_requests,
        "success_requests": success_requests,
        "status_code_counts": status_code_counts,
        "failed_rows": failed_rows,
    }