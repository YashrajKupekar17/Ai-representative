"""Chat endpoint with SSE streaming."""

import json

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.core.agent import run_agent_streaming

router = APIRouter()


class ChatRequest(BaseModel):
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Stream a chat response via Server-Sent Events.

    Events:
      - event: token, data: "text chunk"
      - event: sources, data: [{"tool": "...", "args": "..."}]
      - event: done, data: ""
    """

    def event_generator():
        for chunk_type, data in run_agent_streaming(req.messages):
            if chunk_type == "token":
                yield {"event": "token", "data": data}
            elif chunk_type == "sources":
                yield {"event": "sources", "data": json.dumps(data)}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
