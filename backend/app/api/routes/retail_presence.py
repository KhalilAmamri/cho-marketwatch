from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.schemas.retail_presence import RetailPresenceCountryMetric, RetailPresenceResponse
from app.services.retail_presence_service import get_retail_presence, get_retail_presence_country_metrics

router = APIRouter(prefix="/retail-presence", tags=["retail-presence"])


@router.get("", response_model=RetailPresenceResponse)
def retail_presence(
    country: str | None = Query(default=None, min_length=1),
    current_user: dict = Depends(get_current_user),
):
    del current_user
    normalized_country = country.strip() if country else None

    try:
        return get_retail_presence(country=normalized_country)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/country-metrics", response_model=list[RetailPresenceCountryMetric])
def retail_presence_country_metrics(current_user: dict = Depends(get_current_user)):
    del current_user
    return get_retail_presence_country_metrics()
