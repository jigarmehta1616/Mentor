"""Path endpoint: the ordered learning path with per-concept status."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.engine import get_engine
from app.memory.graph_utils import topological_sort

router = APIRouter(prefix="/paths", tags=["paths"])


@router.get("/{user_id}")
def get_path(user_id: str, topic: str = Query(...)) -> dict[str, object]:
    """Return the topological path and each concept's mastery status.

    Path is built once (O(V + E)); mastery is read per concept (O(log n) each,
    batched in-repo).
    """
    engine = get_engine()
    order = topological_sort(engine.repo.topic_edges(topic))
    learned = engine.repo.learned(user_id, topic)
    concepts = {c.id: c for c in engine.repo.concepts(topic)}

    items = []
    for cid in order:
        ref = concepts.get(cid)
        m = engine.repo.mastery(user_id, cid)
        if cid in learned:
            status = "learned"
        elif m.last_score is not None:
            status = "in-progress"
        else:
            status = "not-started"
        items.append(
            {
                "id": cid,
                "name": ref.name if ref else cid,
                "status": status,
                "mastery_level": round(m.mastery_level, 3),
            }
        )
    return {"user_id": user_id, "topic": topic, "path": items}
