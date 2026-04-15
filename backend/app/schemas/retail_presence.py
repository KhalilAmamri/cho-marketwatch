from typing import Literal

from pydantic import BaseModel


PresenceStatus = Literal["all_present", "partial", "none"]


class RetailPresenceWebsite(BaseModel):
    website_id: int
    site_name: str
    country: str | None = None


class RetailPresenceCell(BaseModel):
    website_id: int
    present: bool


class RetailPresenceFormatRow(BaseModel):
    product_format_id: int
    format: str
    packaging: str
    format_label: str
    presence_status: PresenceStatus
    present_count: int
    missing_count: int
    coverage_rate: float
    cells: list[RetailPresenceCell]


class RetailPresenceProductRow(BaseModel):
    product_id: int
    family_label: str
    presence_status: PresenceStatus
    present_formats: int
    total_formats: int
    formats: list[RetailPresenceFormatRow]


class RetailPresenceKpis(BaseModel):
    total_product_families: int
    total_formats: int
    total_websites: int
    total_active_links: int
    total_matrix_cells: int
    present_cells: int
    missing_cells: int
    coverage_rate: float


class RetailPresenceResponse(BaseModel):
    country: str
    available_countries: list[str]
    country_retailers: dict[str, list[str]]
    websites: list[RetailPresenceWebsite]
    kpis: RetailPresenceKpis
    rows: list[RetailPresenceProductRow]
