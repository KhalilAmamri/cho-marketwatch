from datetime import datetime

from pydantic import BaseModel


class StatusCodeCount(BaseModel):
    status_code: int
    count: int


class FailedRequestRow(BaseModel):
    id: int
    store_name: str
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