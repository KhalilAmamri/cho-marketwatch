from datetime import date
from typing import Literal
from fastapi import APIRouter, Query

from app.schemas.prices import (
    DashboardKpis,
    FiltersResponse,
    MarketChangeRow,
    MarketOverviewResponse,
    PriceAnalysisResponse,
    PricePoint,
    StoreOption,
    WeeklySeriesPoint,
)
from app.services.prices_service import (
    get_filters,
    get_kpis,
    get_available_weeks,
    get_store_universe,
    get_market_changes,
    get_market_overview,
    get_price_analysis,
    get_summary,
    get_timeseries,
)

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
    fx_basis_week_start: date | None = Query(default=None),
    all_weeks: bool = Query(default=False),
    price_mode: Literal["average", "last_scraped"] = Query(default="average"),
    product_variant_id: int | None = Query(default=None, ge=1),
):
    return get_summary(
        week_start=week_start,
        fx_basis_week_start=fx_basis_week_start,
        all_weeks=all_weeks,
        price_mode=price_mode,
        product_variant_id=product_variant_id,
    )


@router.get("/timeseries", response_model=list[WeeklySeriesPoint])
def prices_timeseries(
    product_variant_id: int = Query(..., ge=1),
    website: str | None = Query(default=None),
    country: str | None = Query(default=None),
    store: str | None = Query(default=None),
    weeks: int = Query(default=52, ge=0, le=5200),
    fx_basis_week_start: date | None = Query(default=None),
):
    return get_timeseries(
        product_variant_id=product_variant_id,
        website=website,
        country=country,
        weeks=weeks,
        store=store,
        fx_basis_week_start=fx_basis_week_start,
    )


@router.get("/analysis", response_model=PriceAnalysisResponse)
def prices_analysis(
    product_variant_id: list[int] | None = Query(default=None),
    website: str | None = Query(default=None),
    country: str | None = Query(default=None),
    weeks: int = Query(default=52, ge=4, le=260),
    fx_basis_week_start: date | None = Query(default=None),
):
    return get_price_analysis(
        product_variant_ids=product_variant_id,
        website=website,
        country=country,
        weeks=weeks,
        fx_basis_week_start=fx_basis_week_start,
    )


@router.get("/market-overview", response_model=MarketOverviewResponse)
def prices_market_overview(
    website: str | None = Query(default=None),
    country: str | None = Query(default=None),
    store: str | None = Query(default=None),
    week_start: date | None = Query(default=None),
    fx_basis_week_start: date | None = Query(default=None),
):
    return get_market_overview(
        website=website,
        country=country,
        store=store,
        week_start=week_start,
        fx_basis_week_start=fx_basis_week_start,
    )


@router.get("/market-changes", response_model=list[MarketChangeRow])
def prices_market_changes(
    week_start: date = Query(...),
    previous_week_start: date | None = Query(default=None),
    fx_basis_week_start: date | None = Query(default=None),
    website: str | None = Query(default=None),
    country: str | None = Query(default=None),
    store: str | None = Query(default=None),
    limit: int = Query(default=15, ge=1, le=200),
):
    return get_market_changes(
        week_start=week_start,
        previous_week_start=previous_week_start,
        fx_basis_week_start=fx_basis_week_start,
        website=website,
        country=country,
        store=store,
        limit=limit,
    )


@router.get("/weeks", response_model=list[date])
def prices_weeks(
    website: str | None = Query(default=None),
    country: str | None = Query(default=None),
    store: str | None = Query(default=None),
    limit: int = Query(default=260, ge=1, le=5200),
):
    return get_available_weeks(
        website=website,
        country=country,
        store=store,
        limit=limit,
    )


@router.get("/stores", response_model=list[StoreOption])
def prices_stores(
    website: str | None = Query(default=None),
    country: str | None = Query(default=None),
):
    return get_store_universe(
        website=website,
        country=country,
    )
