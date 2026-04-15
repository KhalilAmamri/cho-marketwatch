from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_admin_user
from app.schemas.retail_presence import RetailPresenceResponse
from app.services.retail_presence_service import get_retail_presence

router = APIRouter(prefix="/retail-presence", tags=["retail-presence"])


@router.get("", response_model=RetailPresenceResponse)
def retail_presence(
    country: str | None = Query(default=None, min_length=1),
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    normalized_country = country.strip() if country else None

    try:
        return get_retail_presence(country=normalized_country)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
