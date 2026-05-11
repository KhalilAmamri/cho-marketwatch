import asyncio
import sys
from importlib import import_module
from pathlib import Path

from psycopg2.extras import RealDictCursor

from app.db.connection import get_connection


STORE_NAME_SQL = """
CASE
    WHEN s.store_name IS NOT NULL AND BTRIM(s.store_name) <> '' THEN s.store_name
    WHEN s.store_code IS NOT NULL THEN w.site_name || ' (' || s.store_code || ')'
    ELSE w.site_name
END
"""

PRODUCT_LABEL_SQL = (
    "b.brand_name || ' ' || c.category_name || ' ' || r.range_name || ' ' || f.format_name || ' ' || pk.packaging_name"
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT_STR = str(PROJECT_ROOT)


def _import_project_symbol(module_name: str, symbol_name: str):
    if PROJECT_ROOT_STR not in sys.path:
        # Uvicorn with --app-dir backend does not always include repository root.
        sys.path.append(PROJECT_ROOT_STR)
    module = import_module(module_name)
    return getattr(module, symbol_name)


def _ensure_windows_proactor_policy() -> None:
    if sys.platform != "win32":
        return

    policy_cls = getattr(asyncio, "WindowsProactorEventLoopPolicy", None)
    if policy_cls is None:
        return

    current_policy = asyncio.get_event_loop_policy()
    if not isinstance(current_policy, policy_cls):
        # On Windows + uvicorn, SelectorPolicy can cause Playwright subprocess startup
        # to fail with NotImplementedError in targeted scraping calls.
        asyncio.set_event_loop_policy(policy_cls())


def _get_raw_operation_row(cur, raw_staging_id: int) -> dict:
    cur.execute(
        f"""
        SELECT
            rs.id AS raw_staging_id,
            pu.id AS product_url_id,
            w.site_name AS website_name,
            {STORE_NAME_SQL} AS store_name,
            {PRODUCT_LABEL_SQL} AS product_label,
            rs.status,
            rs.http_status_code,
            rs.error_message,
            rs.screenshot_path,
            rs.scraped_at,
            rs.processed_at
        FROM raw_staging rs
        JOIN product_urls pu ON rs.product_url_id = pu.id
        JOIN websites w ON pu.website_id = w.id
        LEFT JOIN stores s ON pu.store_id = s.id
        JOIN product_variants pv ON pu.product_variant_id = pv.id
        JOIN products p ON pv.product_id = p.id
        JOIN formats f ON pv.format_id = f.id
        JOIN packagings pk ON pv.packaging_id = pk.id
        JOIN brands b ON p.brand_id = b.id
        JOIN categories c ON p.category_id = c.id
        JOIN ranges r ON p.range_id = r.id
        WHERE rs.id = %s
        """,
        (raw_staging_id,),
    )
    row = cur.fetchone()
    if not row:
        raise LookupError("Raw staging row not found")
    return row


def get_operational_visibility(limit_failed: int = 100) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                WITH latest_by_target AS (
                    SELECT DISTINCT ON (rs.product_url_id)
                        rs.id,
                        rs.product_url_id,
                        rs.status,
                        rs.http_status_code,
                        rs.scraped_at,
                        rs.error_message,
                        rs.screenshot_path
                    FROM raw_staging rs
                    ORDER BY rs.product_url_id, rs.scraped_at DESC, rs.id DESC
                )
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
                FROM latest_by_target
                """
            )
            summary = cur.fetchone() or {}

            cur.execute(
                f"""
                WITH latest_by_target AS (
                    SELECT DISTINCT ON (rs.product_url_id)
                        rs.id,
                        rs.product_url_id,
                        rs.status,
                        rs.http_status_code,
                        rs.scraped_at,
                        rs.error_message,
                        rs.screenshot_path
                    FROM raw_staging rs
                    ORDER BY rs.product_url_id, rs.scraped_at DESC, rs.id DESC
                )
                SELECT
                    rs.id,
                    {STORE_NAME_SQL} AS store_name,
                    {PRODUCT_LABEL_SQL} AS product_label,
                    rs.error_message,
                    rs.screenshot_path,
                    rs.http_status_code,
                    rs.scraped_at
                FROM latest_by_target rs
                JOIN product_urls pu ON rs.product_url_id = pu.id
                JOIN websites w ON pu.website_id = w.id
                LEFT JOIN stores s ON pu.store_id = s.id
                JOIN product_variants pv ON pu.product_variant_id = pv.id
                JOIN products p ON pv.product_id = p.id
                JOIN formats f ON pv.format_id = f.id
                JOIN packagings pk ON pv.packaging_id = pk.id
                JOIN brands b ON p.brand_id = b.id
                JOIN categories c ON p.category_id = c.id
                JOIN ranges r ON p.range_id = r.id
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


def get_operation_logs(limit: int = 200) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT
                    rs.id AS raw_staging_id,
                    pu.id AS product_url_id,
                    w.site_name AS website_name,
                    {STORE_NAME_SQL} AS store_name,
                    {PRODUCT_LABEL_SQL} AS product_label,
                    rs.status,
                    rs.http_status_code,
                    rs.error_message,
                    rs.screenshot_path,
                    rs.scraped_at,
                    rs.processed_at
                FROM raw_staging rs
                JOIN product_urls pu ON rs.product_url_id = pu.id
                JOIN websites w ON pu.website_id = w.id
                LEFT JOIN stores s ON pu.store_id = s.id
                JOIN product_variants pv ON pu.product_variant_id = pv.id
                JOIN products p ON pv.product_id = p.id
                JOIN formats f ON pv.format_id = f.id
                JOIN packagings pk ON pv.packaging_id = pk.id
                JOIN brands b ON p.brand_id = b.id
                JOIN categories c ON p.category_id = c.id
                JOIN ranges r ON p.range_id = r.id
                ORDER BY rs.scraped_at DESC, rs.id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return {"rows": rows}


def _execute_targeted_scrape(
    *,
    product_url_id: int,
    mode: str,
    retry_of_raw_id: int | None = None,
    headless_override: bool = False,
) -> dict:
    _ensure_windows_proactor_policy()

    run_etl = _import_project_symbol("etl.run_etl", "run_etl")
    run_single_product_url = _import_project_symbol("scrapers.scraper_manager", "run_single_product_url")

    scrape_result = run_single_product_url(int(product_url_id), headless_override=headless_override)
    raw_staging_id = scrape_result.get("raw_staging_id")
    if not raw_staging_id:
        raise RuntimeError("Scrape finished without raw_staging row")

    if scrape_result.get("status") == "pending":
        run_etl(raw_ids=[int(raw_staging_id)])

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            raw_row = _get_raw_operation_row(cur, int(raw_staging_id))

    status = raw_row.get("status")
    if status == "processed":
        message = "Scraping operation completed successfully"
    elif status == "failed":
        message = "Scraping operation failed"
    else:
        message = "Scraping operation completed"

    return {
        "mode": mode,
        "message": message,
        "raw_row": raw_row,
        "retry_of_raw_id": retry_of_raw_id,
    }


def trigger_product_url_scrape(product_url_id: int, headless_override: bool = False) -> dict:
    return _execute_targeted_scrape(
        product_url_id=int(product_url_id),
        mode="manual",
        retry_of_raw_id=None,
        headless_override=headless_override,
    )


def retry_failed_scrape(raw_staging_id: int, headless_override: bool = False) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, product_url_id, status
                FROM raw_staging
                WHERE id = %s
                """,
                (int(raw_staging_id),),
            )
            row = cur.fetchone()

    if not row:
        raise LookupError("Failed row not found")

    if row["status"] != "failed":
        raise ValueError("Only failed rows can be retried")

    return _execute_targeted_scrape(
        product_url_id=int(row["product_url_id"]),
        mode="retry",
        retry_of_raw_id=int(raw_staging_id),
        headless_override=headless_override,
    )