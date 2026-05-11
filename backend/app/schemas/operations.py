from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StatusCodeCount(BaseModel):
    status_code: int
    count: int


class FailedRequestRow(BaseModel):
    id: int
    store_name: str
    product_label: str
    error_message: str | None = None
    screenshot_path: str | None = None
    http_status_code: int | None = None
    scraped_at: datetime


class OperationalVisibilityResponse(BaseModel):
    success_rate: float
    total_records: int
    failed_requests: int
    success_requests: int
    status_code_counts: list[StatusCodeCount]
    failed_rows: list[FailedRequestRow]


class OperationLogRow(BaseModel):
    raw_staging_id: int
    product_url_id: int
    website_name: str
    store_name: str
    product_label: str
    status: Literal["pending", "processed", "failed"]
    http_status_code: int | None = None
    error_message: str | None = None
    screenshot_path: str | None = None
    scraped_at: datetime
    processed_at: datetime | None = None


class OperationLogsResponse(BaseModel):
    rows: list[OperationLogRow]


class ScrapeActionResponse(BaseModel):
    mode: Literal["manual", "retry"]
    message: str
    raw_row: OperationLogRow
    retry_of_raw_id: int | None = None