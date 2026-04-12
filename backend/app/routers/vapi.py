"""
Vapi voice agent webhook.

Vapi sends POST requests here when the assistant needs to execute a function.
We run the tool and return the result so Vapi can feed it back to the LLM.
"""

import json
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.tools import execute_tool

router = APIRouter(prefix="/vapi")
logger = structlog.get_logger()


@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Handle Vapi server messages.

    Message types we care about:
    - "function-call": single function call (legacy)
    - "tool-calls": batch tool calls (current)
    - "assistant-request": return assistant config dynamically (optional)
    - "end-of-call-report": log call summary
    """
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type", "")

    logger.info("vapi_webhook", type=msg_type)

    # --- Tool calls (current Vapi format) ---
    if msg_type == "tool-calls":
        tool_call_list = message.get("toolCallList", [])
        results = []
        for tc in tool_call_list:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            arguments = fn.get("arguments", "{}")

            # Vapi sends arguments as a dict, execute_tool expects a JSON string
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments)

            logger.info("vapi_tool_call", tool=name)
            result = execute_tool(name, arguments)
            results.append({
                "toolCallId": tc.get("id", ""),
                "result": result,
            })

        return JSONResponse({"results": results})

    # --- Single function call (legacy format) ---
    if msg_type == "function-call":
        fn_call = message.get("functionCall", {})
        name = fn_call.get("name", "")
        parameters = fn_call.get("parameters", {})

        logger.info("vapi_function_call", tool=name)
        result = execute_tool(name, json.dumps(parameters))

        return JSONResponse({"result": result})

    # --- End of call report ---
    if msg_type == "end-of-call-report":
        duration = message.get("endedReason", "unknown")
        logger.info("vapi_call_ended", reason=duration)
        return JSONResponse({"ok": True})

    # --- Everything else (status-update, etc.) ---
    return JSONResponse({"ok": True})
