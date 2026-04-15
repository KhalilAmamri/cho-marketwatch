from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NamedLookup(BaseModel):
    id: int
    name: str


class NamedLookupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WebsiteLookup(BaseModel):
    id: int
    site_name: str
    base_url: str
    country: str
    scraper_status: Literal["active", "pending"]


class WebsiteCreate(BaseModel):
    site_name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., min_length=1, max_length=500)
    country: str = Field(..., min_length=1, max_length=50)


class WebsiteUpdate(WebsiteCreate):
    pass


class WebsiteRow(BaseModel):
    id: int
    site_name: str
    base_url: str
    country: str
    scraper_status: Literal["active", "pending"]
    created_at: datetime | None = None


class StoreLookup(BaseModel):
    id: int
    website_id: int
    website_name: str
    store_code: str
    store_name: str | None = None
    label: str


class ProductFormatLookup(BaseModel):
    id: int
    label: str


class StoreCreate(BaseModel):
    website_id: int = Field(..., gt=0)
    store_code: str = Field(..., min_length=1, max_length=50)
    store_name: str | None = Field(default=None, max_length=200)


class StoreUpdate(StoreCreate):
    pass


class StoreRow(BaseModel):
    id: int
    website_id: int
    website_name: str
    country: str | None = None
    store_code: str
    store_name: str | None = None
    label: str
    created_at: datetime | None = None


class AdminLookupsResponse(BaseModel):
    brands: list[NamedLookup]
    categories: list[NamedLookup]
    ranges: list[NamedLookup]
    websites: list[WebsiteLookup]
    stores: list[StoreLookup]
    product_formats: list[ProductFormatLookup]
    formats: list[str]
    packagings: list[str]


class ProductFormatCreate(BaseModel):
    brand_id: int = Field(..., gt=0)
    category_id: int = Field(..., gt=0)
    range_id: int = Field(..., gt=0)
    format: str = Field(..., min_length=1, max_length=50)
    packaging: str = Field(..., min_length=1, max_length=50)


class ProductFormatUpdate(ProductFormatCreate):
    pass


class ProductFormatRow(BaseModel):
    id: int
    product_id: int
    brand_id: int
    brand_name: str
    category_id: int
    category_name: str
    range_id: int
    range_name: str
    format: str
    packaging: str
    created_at: datetime | None = None


class ProductUrlCreate(BaseModel):
    website_id: int = Field(..., gt=0)
    store_id: int | None = Field(default=None, gt=0)
    product_format_id: int = Field(..., gt=0)
    url: str = Field(..., min_length=1, max_length=1000)
    is_active: bool = True


class ProductUrlUpdate(ProductUrlCreate):
    pass


class ProductUrlActiveUpdate(BaseModel):
    is_active: bool


class ProductUrlRow(BaseModel):
    id: int
    website_id: int
    website_name: str
    country: str | None = None
    store_id: int | None = None
    store_code: str | None = None
    product_format_id: int
    product_label: str
    url: str
    is_active: bool
    created_at: datetime | None = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)
    role: Literal["admin", "user"] = "user"
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserRow(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    role: Literal["admin", "user"]
    is_active: bool
    created_at: datetime | None = None
    last_login: datetime | None = None
