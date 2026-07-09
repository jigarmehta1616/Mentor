"""Apply schema.sql to DATABASE_URL and seed starter concept DAGs.

Run with:  python -m app.db.migrate
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from app.db.engine import get_engine
from app.lib.logger import get_logger

logger = get_logger()

_SCHEMA = Path(__file__).with_name("schema.sql")


def apply_schema() -> None:
    """Execute schema.sql (idempotent — uses IF NOT EXISTS everywhere)."""
    sql = _SCHEMA.read_text(encoding="utf-8")
    engine = get_engine()
    with engine.begin() as conn:
        for statement in _split_statements(sql):
            conn.execute(text(statement))
    logger.info("Schema applied.")


def _split_statements(sql: str) -> list[str]:
    """Split on ';' at statement boundaries, dropping comment-only chunks."""
    out: list[str] = []
    for chunk in sql.split(";"):
        stripped = "\n".join(
            line for line in chunk.splitlines() if not line.strip().startswith("--")
        ).strip()
        if stripped:
            out.append(stripped)
    return out


def main() -> None:
    apply_schema()
    from app.seed.concepts import seed_all

    seed_all()


if __name__ == "__main__":
    main()
