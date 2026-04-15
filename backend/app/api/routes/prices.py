from datetime import date
from fastapi import APIRouter, Query

from app.schemas.prices import DashboardKpis, FiltersResponse, PricePoint, WeeklySeriesPoint
from app.services.prices_service import get_filters, get_kpis, get_summary, get_timeseries

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/kpis", response_model=DashboardKpis)
def prices_kpis():
    return get_kpis()


@router.get("/filters", response_model=FiltersResponse)
def price_filters():
    return get_filters()


@router.get("/summary", response_model=list[PricePoint])
def prices_summary(
    week_start: date | None = Query(default=None),
    all_weeks: bool = Query(default=False),
):
    return get_summary(week_start=week_start, all_weeks=all_weeks)


@router.get("/timeseries", response_model=list[WeeklySeriesPoint])
def prices_timeseries(
    product: str,
    website: str | None = Query(default=None),
    country: str | None = Query(default=None),
    store: str | None = Query(default=None),
    weeks: int = Query(default=52, ge=4, le=260),
):
    return get_timeseries(product=product, website=website, country=country, weeks=weeks, store=store)
