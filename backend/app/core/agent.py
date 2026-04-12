"""
Core agent: GPT-4o with function calling.
Handles the tool-call loop: LLM decides tools → execute → feed back → generate response.
"""

from openai import OpenAI

from app.config import settings
from app.core.prompts import get_system_prompt
from app.core.tools import TOOL_SCHEMAS, execute_tool

client = OpenAI(api_key=settings.openai_api_key)


def run_agent(messages: list[dict]) -> dict:
    """
    Run the agent with a conversation history.
    messages: [{"role": "user"|"assistant", "content": "..."}]
    Returns: {"response": str, "sources": list}

    The agent loops: call GPT-4o → if tool calls, execute them → feed results
    back → call GPT-4o again → until it produces a final text response.
    """
    # Build full message list with system prompt
    full_messages = [{"role": "system", "content": get_system_prompt()}] + messages

    sources = []
    max_iterations = 5  # safety limit on tool-call loops

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=full_messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # If no tool calls, we have the final response
        if not message.tool_calls:
            return {
                "response": message.content or "",
                "sources": sources,
            }

        # Process tool calls
        full_messages.append(message.model_dump())

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            result = execute_tool(tool_name, tool_args)

            # Track sources for transparency
            sources.append({
                "tool": tool_name,
                "args": tool_args,
            })

            full_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    # If we hit max iterations, return whatever we have
    return {
        "response": "I'm having trouble processing that request. Could you rephrase?",
        "sources": sources,
    }


def run_agent_streaming(messages: list[dict]):
    """
    Streaming version: yields text chunks as they come.
    First resolves all tool calls (non-streaming), then streams the final response.
    Returns a generator of (chunk_type, data) tuples:
      ("token", "text...")  — streamed response tokens
      ("sources", [...])    — source list at the end
    """
    full_messages = [{"role": "system", "content": get_system_prompt()}] + messages
    sources = []
    max_iterations = 5

    for _ in range(max_iterations):
        # Non-streaming call to check for tool calls
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=full_messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if not message.tool_calls:
            # No tool calls — now stream the final response
            break

        # Execute tool calls
        full_messages.append(message.model_dump())

        for tool_call in message.tool_calls:
            result = execute_tool(tool_call.function.name, tool_call.function.arguments)
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
    stream = client.chat.completions.create(
        model=settings.llm_model,
        messages=full_messages,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield ("token", delta.content)

    yield ("sources", sources)
