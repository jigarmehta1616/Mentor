"""Session endpoints: start a session and drive the interactive teaching loop."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.engine import get_engine
from app.api.schemas import StartSessionRequest, TurnRequest
from app.api.views import turn_view

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("")
def start_session(req: StartSessionRequest) -> dict[str, object]:
    """Start a session → returns due reviews + the first concept (teach + quiz)."""
    engine = get_engine()
    session_id, state = engine.start(req.user_id, req.topic, req.level)
    return turn_view(engine, session_id, state)


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/{session_id}/turn")
def turn(session_id: str, req: TurnRequest) -> StreamingResponse:
    """Drive one agent step, streaming the explanation then a final view (SSE)."""
    engine = get_engine()
    try:
        state = engine.turn(session_id, req.answer)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc

    view = turn_view(engine, session_id, state)

    def stream() -> Iterator[str]:
        if view.get("grade"):
            yield _sse("grade", view["grade"])
        explanation = view.get("explanation") or ""
        # Stream the explanation in word chunks for a live chat feel.
        for word in explanation.split(" "):
            yield _sse("token", word + " ")
        yield _sse("done", view)

    return StreamingResponse(stream(), media_type="text/event-stream")
