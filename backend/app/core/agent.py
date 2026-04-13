"""
Core agent: GPT-4o with function calling.
Handles the tool-call loop: LLM decides tools -> execute -> feed back -> generate response.
Includes semantic caching, observability, and Opik tracing.
"""

import time

from openai import OpenAI

from app.config import settings
from app.core.prompts import get_system_prompt, PROMPT_VERSION
from app.core.tools import TOOL_SCHEMAS, execute_tool
from app.services.cache import cache_lookup, cache_store
from app.services.observability import AgentTrace, LLMTrace, ToolTrace

# --- Opik setup ---
_opik_enabled = False
try:
    if settings.opik_api_key:
        import opik
        from opik.integrations.openai import track_openai

        opik.configure(
            api_key=settings.opik_api_key,
            workspace=settings.opik_workspace,
            force=True,
        )
        _opik_enabled = True
except Exception:
    pass  # Opik is optional — runs fine without it

client = OpenAI(api_key=settings.openai_api_key)
if _opik_enabled:
    client = track_openai(client, project_name=settings.opik_project)


def _get_latest_user_query(messages: list[dict]) -> str:
    """Extract the most recent user message for caching/logging."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _track_agent(func):
    """Apply Opik @track decorator if Opik is enabled, otherwise no-op."""
    if _opik_enabled:
        from opik import track
        return track(
            name=func.__name__,
            project_name=settings.opik_project,
            tags=["agent", f"prompt-v{PROMPT_VERSION}"],
        )(func)
    return func


@_track_agent
def run_agent(messages: list[dict]) -> dict:
    """
    Run the agent with a conversation history.
    messages: [{"role": "user"|"assistant", "content": "..."}]
    Returns: {"response": str, "sources": list}
    """
    trace = AgentTrace(query=_get_latest_user_query(messages), prompt_version=PROMPT_VERSION)
    agent_start = time.time()

    # --- Semantic cache check ---
    cached = cache_lookup(trace.query)
    if cached:
        trace.cache_hit = True
        trace.total_duration_ms = round((time.time() - agent_start) * 1000)
        trace.log()
        return cached

    # --- Full agent pipeline ---
    full_messages = [{"role": "system", "content": get_system_prompt()}] + messages
    sources = []
    max_iterations = 5

    for iteration in range(max_iterations):
        trace.iterations = iteration + 1

        llm_start = time.time()
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=full_messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        llm_ms = round((time.time() - llm_start) * 1000)

        usage = response.usage
        trace.llm_traces.append(LLMTrace(
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            duration_ms=llm_ms,
        ))

        message = response.choices[0].message

        if not message.tool_calls:
            result = {
                "response": message.content or "",
                "sources": sources,
            }
            trace.total_duration_ms = round((time.time() - agent_start) * 1000)
            trace.log()

            # Store in cache for future queries
            cache_store(trace.query, result["response"], result["sources"])
            return result

        # Process tool calls
        full_messages.append(message.model_dump())

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            tool_start = time.time()
            result = execute_tool(tool_name, tool_args)
            tool_ms = round((time.time() - tool_start) * 1000)

            trace.tool_traces.append(ToolTrace(
                name=tool_name,
                args=tool_args,
                result_length=len(result),
                duration_ms=tool_ms,
            ))

            sources.append({
                "tool": tool_name,
                "args": tool_args,
            })

            full_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # Max iterations hit
    trace.total_duration_ms = round((time.time() - agent_start) * 1000)
    trace.log()
    return {
        "response": "I'm having trouble processing that request. Could you rephrase?",
        "sources": sources,
    }


@_track_agent
def run_agent_streaming(messages: list[dict]):
    """
    Streaming version: yields text chunks as they come.
    First resolves all tool calls (non-streaming), then streams the final response.
    Returns a generator of (chunk_type, data) tuples:
      ("token", "text...")  -- streamed response tokens
      ("sources", [...])    -- source list at the end
    """
    trace = AgentTrace(query=_get_latest_user_query(messages), prompt_version=PROMPT_VERSION)
    agent_start = time.time()

    # --- Semantic cache check ---
    cached = cache_lookup(trace.query)
    if cached:
        trace.cache_hit = True
        trace.total_duration_ms = round((time.time() - agent_start) * 1000)
        trace.log()
        # Stream cached response token-by-token for consistent UX
        yield ("token", cached["response"])
        yield ("sources", cached["sources"])
        return

    # --- Full agent pipeline ---
    full_messages = [{"role": "system", "content": get_system_prompt()}] + messages
    sources = []
    max_iterations = 5

    for iteration in range(max_iterations):
        trace.iterations = iteration + 1

        llm_start = time.time()
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=full_messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        llm_ms = round((time.time() - llm_start) * 1000)

        usage = response.usage
        trace.llm_traces.append(LLMTrace(
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            duration_ms=llm_ms,
        ))

        message = response.choices[0].message

        if not message.tool_calls:
            break

        # Execute tool calls
        full_messages.append(message.model_dump())

        for tool_call in message.tool_calls:
            tool_start = time.time()
            result = execute_tool(tool_call.function.name, tool_call.function.arguments)
            tool_ms = round((time.time() - tool_start) * 1000)

            trace.tool_traces.append(ToolTrace(
                name=tool_call.function.name,
                args=tool_call.function.arguments,
                result_length=len(result),
                duration_ms=tool_ms,
            ))

            sources.append({
                "tool": tool_call.function.name,
                "args": tool_call.function.arguments,
            })
            full_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # Stream the final response
    stream_start = time.time()
    stream = client.chat.completions.create(
        model=settings.llm_model,
        messages=full_messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    full_response = []
    for chunk in stream:
        # Capture usage from the final chunk
        if chunk.usage:
            trace.llm_traces.append(LLMTrace(
                prompt_tokens=chunk.usage.prompt_tokens,
                completion_tokens=chunk.usage.completion_tokens,
                total_tokens=chunk.usage.total_tokens,
                duration_ms=round((time.time() - stream_start) * 1000),
            ))

        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            full_response.append(delta.content)
            yield ("token", delta.content)

    trace.total_duration_ms = round((time.time() - agent_start) * 1000)
    trace.log()

    # Cache the full response
    response_text = "".join(full_response)
    cache_store(trace.query, response_text, sources)

    yield ("sources", sources)
