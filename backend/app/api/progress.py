"""Progress endpoint: mastery per concept + paginated quiz history."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.engine import get_engine

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/{user_id}")
def get_progress(
    user_id: str,
    topic: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, object]:
    """Mastery per concept plus a paginated slice of quiz history.

    History is indexed + paginated (O(log n + page)); no SELECT * of full history.
    """
    engine = get_engine()
    concepts = engine.repo.concepts(topic)
    mastery = []
    for ref in concepts:
        m = engine.repo.mastery(user_id, ref.id)
        mastery.append(
            {
                "id": ref.id,
                "name": ref.name,
                "mastery_level": round(m.mastery_level, 3),
                "repetitions": m.repetitions,
                "interval_days": m.interval_days,
                "last_score": m.last_score,
                "next_review": str(m.next_review) if m.next_review else None,
            }
        )
    history = engine.repo.attempt_history(user_id, limit=limit, offset=offset)
    return {
        "user_id": user_id,
        "topic": topic,
        "mastery": mastery,
        "history": history,
        "page": {"limit": limit, "offset": offset, "count": len(history)},
    }
