"""
Tool definitions for GPT-4o function calling.
Each tool has: an OpenAI function schema + an execute function.
"""

import json
from app.services.knowledge import lookup_facts, search_knowledge
from app.services.calendar_client import get_available_slots, book_meeting

# --- OpenAI function schemas ---

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_facts",
            "description": (
                "Look up structured facts about Yashraj from his personal profile. "
                "Use for direct factual questions: name, education, skills, "
                "github repos list, strengths, weaknesses, availability, why hire him. "
                "Categories: education, experience, skills, github_repos, "
                "why_hire, strengths, weaknesses, availability, all"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "education", "experience", "skills", "github_repos",
                            "why_hire", "strengths", "weaknesses", "availability", "all",
                        ],
                        "description": "The category of facts to look up",
                    }
                },
                "required": ["category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "Search Yashraj's resume, project details, and GitHub READMEs "
                "for detailed or nuanced information. Use when the question needs "
                "context beyond simple facts — project tradeoffs, experience details, "
                "technical depth, specific accomplishments."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "source_filter": {
                        "type": "string",
                        "enum": ["resume", "github", "personal"],
                        "description": "Optional: filter results to a specific source",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": (
                "Get Yashraj's available meeting slots from his calendar. "
                "Use when someone wants to schedule a call or meeting."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format. Defaults to today.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format. Defaults to 7 days from now.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_meeting",
            "description": (
                "Book a meeting with Yashraj. Requires the attendee's name, "
                "email, and a specific time slot. Always confirm these details "
                "with the user before booking."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Attendee's full name",
                    },
                    "email": {
                        "type": "string",
                        "description": "Attendee's email address",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Meeting start time in ISO format, e.g. 2024-01-15T10:00:00.000Z",
                    },
                },
                "required": ["name", "email", "start_time"],
            },
        },
    },
]


# --- Tool execution ---

def execute_tool(name: str, arguments: str) -> str:
    """Execute a tool call and return the result as a string."""
    args = json.loads(arguments)

    if name == "lookup_facts":
        return lookup_facts(args["category"])

    elif name == "search_knowledge":
        return search_knowledge(
            args["query"],
            source_filter=args.get("source_filter"),
        )

    elif name == "get_available_slots":
        slots = get_available_slots(
            start_date=args.get("start_date"),
            end_date=args.get("end_date"),
        )
        if not slots:
            return "No available slots found in the given date range."
        # Format slots nicely for the LLM
        from collections import defaultdict
        by_date = defaultdict(list)
        for s in slots:
            date = s["time"][:10]
            time_str = s["time"][11:16]
            by_date[date].append(time_str)
        lines = []
        for date, times in sorted(by_date.items()):
            lines.append(f"{date}: {', '.join(times)}")
        return "Available slots (UTC):\n" + "\n".join(lines)

    elif name == "book_meeting":
        result = book_meeting(
            name=args["name"],
            email=args["email"],
            start_time=args["start_time"],
        )
        return json.dumps(result)

    else:
        return f"Unknown tool: {name}"
