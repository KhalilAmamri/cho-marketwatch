from fastapi import APIRouter, Depends, Query

from app.core.security import require_admin_user
from app.schemas.operations import OperationalVisibilityResponse
from app.services.operations_service import get_operational_visibility

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/visibility", response_model=OperationalVisibilityResponse)
def operations_visibility(
    limit_failed: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    return get_operational_visibility(limit_failed=limit_failed)