"""SQLAlchemy engine + session factory. One engine per process."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def _normalized_url() -> str:
    """Map a bare ``postgresql://`` URL to the psycopg v3 driver."""
    url = get_settings().database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide engine. O(1) after first call."""
    return create_engine(_normalized_url(), pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yield a session and always close it."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
