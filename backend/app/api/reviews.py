"""Reviews endpoint: items due now (uses the O(log n + k) indexed query)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.api.engine import get_engine

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/{user_id}")
def get_reviews(user_id: str, limit: int = Query(20, ge=1, le=100)) -> dict[str, object]:
    """Return concepts due for review now. O(log n + k) via idx_due."""
    engine = get_engine()
    due_ids = engine.repo.due(user_id, datetime.now(UTC), limit=limit)
    items = []
    for cid in due_ids:
        ref = engine.repo.concept(cid)
        m = engine.repo.mastery(user_id, cid)
        items.append(
            {
                "id": cid,
                "name": ref.name,
                "next_review": str(m.next_review) if m.next_review else None,
                "mastery_level": round(m.mastery_level, 3),
            }
        )
    return {"user_id": user_id, "due": items}
