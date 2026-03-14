from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str


class TimestampedModel(BaseModel):
    created_at: datetime

