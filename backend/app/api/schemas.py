"""Request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import ExplainLevel


class StartSessionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    level: ExplainLevel = "student"


class TurnRequest(BaseModel):
    answer: str | None = None
