from fastapi import APIRouter, Query

from app.schemas.prices import ForecastPoint
from app.services.prices_service import get_forecasts

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("", response_model=list[ForecastPoint])
def forecasts(product: str = Query(..., min_length=3)):
    return get_forecasts(product=product)
