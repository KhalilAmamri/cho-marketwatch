import traceback

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_admin_user
from app.schemas.operations import OperationLogsResponse, OperationalVisibilityResponse, ScrapeActionResponse
from app.services.operations_service import (
    get_operation_logs,
    get_operational_visibility,
    retry_failed_scrape,
    trigger_product_url_scrape,
)

router = APIRouter(prefix="/operations", tags=["operations"])


def _error_detail(exc: Exception) -> str:
    detail = str(exc).strip()
    if detail:
        return detail

    trace = traceback.extract_tb(exc.__traceback__)
    if trace:
        frame = trace[-1]
        return f"{exc.__class__.__name__} at {frame.filename}:{frame.lineno}"

    return f"{exc.__class__.__name__}"


def _to_http_error(exc: Exception):
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_error_detail(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_error_detail(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_error_detail(exc)) from exc


@router.get("/visibility", response_model=OperationalVisibilityResponse)
def operations_visibility(
    limit_failed: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    return get_operational_visibility(limit_failed=limit_failed)


@router.get("/logs", response_model=OperationLogsResponse)
def operations_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    return get_operation_logs(limit=limit)


@router.post("/scrape/product-url/{product_url_id}", response_model=ScrapeActionResponse)
def operations_scrape_product_url(
    product_url_id: int,
    headless: bool = Query(default=False),
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    try:
        return trigger_product_url_scrape(product_url_id=product_url_id, headless_override=headless)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.post("/retry/raw/{raw_staging_id}", response_model=ScrapeActionResponse)
def operations_retry_raw_row(
    raw_staging_id: int,
    headless: bool = Query(default=False),
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    try:
        return retry_failed_scrape(raw_staging_id=raw_staging_id, headless_override=headless)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)