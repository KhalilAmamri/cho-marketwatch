from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel

DataStatus = Literal["OK", "MISSING", "PARTIAL"]


class ProductFilterOption(BaseModel):
    product_variant_id: int
    label: str
    family_label: str
    variant_label: str
    brand: str
    category: str
    range_name: str
    format: str
    packaging: str


class PricePoint(BaseModel):
    product_variant_id: int
    product: str
    family_label: str
    variant_label: str
    brand: str
    category: str
    range_name: str
    format: str
    packaging: str
    website: str
    country: str | None
    store: str
    currency: str
    price: float | None
    base_price: float | None = None
    is_discounted: bool | None = None
    price_eur: float | None
    unit_price_eur: float | None = None
    unit_label: str | None = None
    data_status: DataStatus
    source_url: str | None = None
    screenshot_path: str | None = None
    week_start: date


class WeeklySeriesPoint(BaseModel):
    week_start: date
    avg_price_eur: float | None
    avg_unit_price_eur: float | None = None
    unit_label: str | None = None
    sample_count: int
    data_status: DataStatus


class FiltersResponse(BaseModel):
    products: list[ProductFilterOption]
    websites: list[str]
    countries: list[str]
    currencies: list[str]


class StoreOption(BaseModel):
    store: str
    country: str | None = None


class DashboardKpis(BaseModel):
    latest_week_start: date | None = None
    last_refreshed_at: datetime | None = None
    last_update: datetime | None = None
    products_tracked: int
    websites_tracked: int
    stores_tracked: int
    latest_week_records: int


class PriceAnalysisKpis(BaseModel):
    latest_week_start: date | None = None
    products: int
    stores: int
    countries: int
    avg_price_eur: float | None = None
    max_price_eur: float | None = None
    min_price_eur: float | None = None
    unit_label: str | None = None


class ClusteredBarRank(BaseModel):
    rank: int
    store: str
    country: str | None = None
    unit_price_eur: float | None
    price_eur: float | None = None


class ClusteredBarGroup(BaseModel):
    product_variant_id: int
    product: str
    ranks: list[ClusteredBarRank]


class StoreShareSlice(BaseModel):
    store: str
    country: str | None = None
    records: int


class PriceAnalysisResponse(BaseModel):
    kpis: PriceAnalysisKpis
    clustered: list[ClusteredBarGroup]
    trend: list[WeeklySeriesPoint]
    store_share: list[StoreShareSlice]


class MarketOverviewKpis(BaseModel):
    latest_week_start: date | None = None
    products: int
    stores: int
    countries: int
    avg_discount_pct: float | None = None
    avg_unit_price_eur: float | None = None
    max_unit_price_eur: float | None = None
    min_unit_price_eur: float | None = None
    unit_label: str | None = None


class StoreUnitRankingRow(BaseModel):
    store: str
    country: str | None = None
    avg_unit_price_eur: float | None
    sample_count: int


class StorePresenceSlice(BaseModel):
    store: str
    country: str | None = None
    records: int


class MarketOverviewResponse(BaseModel):
    kpis: MarketOverviewKpis
    store_rankings: list[StoreUnitRankingRow]
    store_presence: list[StorePresenceSlice]


class MarketChangeRow(BaseModel):
    product_variant_id: int
    product: str
    this_week_unit_price_eur: float | None
    last_week_unit_price_eur: float | None
    delta_unit_price_eur: float | None
    delta_pct: float | None
    has_discount: bool
    screenshot_path: str | None = None
    source_url: str | None = None
    example_store: str | None = None
    example_country: str | None = None
