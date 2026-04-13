"""Chat endpoint with SSE streaming."""

import json

from fastapi import APIRouter, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from app.core.agent import run_agent_streaming

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ChatRequest(BaseModel):
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(req: ChatRequest, request: Request):
    """
    Stream a chat response via Server-Sent Events.

    Events:
      - event: token, data: "text chunk"
      - event: sources, data: [{"tool": "...", "args": "..."}]
      - event: done, data: ""

    Rate limited to 20 requests/minute per IP.
    """

    def event_generator():
        for chunk_type, data in run_agent_streaming(req.messages):
            if chunk_type == "token":
                yield {"event": "token", "data": data}
            elif chunk_type == "sources":
                yield {"event": "sources", "data": json.dumps(data)}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
