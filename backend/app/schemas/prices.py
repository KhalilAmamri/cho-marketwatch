from datetime import datetime, date
from pydantic import BaseModel


class PricePoint(BaseModel):
    product: str
    website: str
    country: str | None
    store: str
    currency: str
    price: float
    price_eur: float | None
    source_url: str | None = None
    screenshot_path: str | None = None
    week_start: date


class WeeklySeriesPoint(BaseModel):
    week_start: date
    avg_price_eur: float | None
    sample_count: int


class ForecastPoint(BaseModel):
    forecast_date: date
    predicted_price: float
    price_low: float | None
    price_high: float | None
    confidence_level: str | None
    training_points: int | None
    coverage_rate: float | None = None
    last_observed_week: date | None = None
    store: str


class FiltersResponse(BaseModel):
    products: list[str]
    websites: list[str]
    countries: list[str]
    currencies: list[str]


class DashboardKpis(BaseModel):
    latest_week_start: date | None = None
    last_refreshed_at: datetime | None = None
    last_update: datetime | None = None
    products_tracked: int
    websites_tracked: int
    stores_tracked: int
    latest_week_records: int
