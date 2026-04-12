"""
Create or update the Vapi assistant via API.
Run: cd backend && source .venv/bin/activate && python setup_vapi.py

Prerequisites:
  1. Sign up at https://vapi.ai (free tier)
  2. Add VAPI_API_KEY to your .env
  3. Deploy the backend so you have a public SERVER_URL (or use ngrok for local testing)

Usage:
  python setup_vapi.py                          # Create new assistant
  python setup_vapi.py --server-url https://...  # Override server URL
  python setup_vapi.py --update <assistant_id>   # Update existing assistant
"""

import argparse
import json
import sys

import httpx
from app.config import settings
from app.core.prompts import get_system_prompt

VAPI_BASE = "https://api.vapi.ai"


VOICE_ADDENDUM = """
VOICE-SPECIFIC RULES (you are on a phone call):
- Keep responses SHORT — 2-3 sentences max. Offer to elaborate if they want more.
- NEVER read out URLs, links, or GitHub paths. Instead say "I can send you the details" or "you'll find it on his GitHub".
- NEVER read out long lists. Pick the top 2 most relevant items, briefly describe each in one sentence, then say "and several more — want me to go on?"
- When listing meeting slots, give 3-4 options max, not the entire list.
- ALWAYS repeat back the chosen time slot to confirm before asking for name/email. Example: "So that's 8:30 AM UTC tomorrow — correct?"
- Speak naturally. Use contractions. Avoid jargon unless the caller uses it first.
- Spell out the caller's email back to them letter by letter to confirm before booking.

PRONUNCIATION GUIDE:
- Yashraj Kupekar is pronounced "Yash-rahj Koo-pay-kar"
- Guftagu is pronounced "Guf-ta-goo"
"""


def get_assistant_config(server_url: str) -> dict:
    """Build the Vapi assistant configuration."""
    voice_prompt = get_system_prompt() + VOICE_ADDENDUM
    return {
        "name": "Yashraj AI Persona",
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": voice_prompt},
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_facts",
                        "description": (
                            "Look up structured facts about Yashraj. "
                            "Categories: education, experience, skills, github_repos, "
                            "why_hire, strengths, weaknesses, availability, all"
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "category": {
                                    "type": "string",
                                    "enum": [
                                        "education", "experience", "skills",
                                        "github_repos", "why_hire", "strengths",
                                        "weaknesses", "availability", "all",
                                    ],
                                }
                            },
                            "required": ["category"],
                        },
                    },
                    "async": False,
                    "server": {"url": f"{server_url}/vapi/webhook"},
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_knowledge",
                        "description": (
                            "Search Yashraj's resume, project details, and GitHub READMEs "
                            "for detailed or nuanced information."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "source_filter": {
                                    "type": "string",
                                    "enum": ["resume", "github", "personal"],
                                },
                            },
                            "required": ["query"],
                        },
                    },
                    "async": False,
                    "server": {"url": f"{server_url}/vapi/webhook"},
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_available_slots",
                        "description": (
                            "Get Yashraj's available meeting slots from his calendar."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {"type": "string"},
                                "end_date": {"type": "string"},
                            },
                            "required": [],
                        },
                    },
                    "async": False,
                    "server": {"url": f"{server_url}/vapi/webhook"},
                },
                {
                    "type": "function",
                    "function": {
                        "name": "book_meeting",
                        "description": (
                            "Book a meeting with Yashraj. Requires name, email, "
                            "and start_time. Always confirm details before booking."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "start_time": {"type": "string"},
                            },
                            "required": ["name", "email", "start_time"],
                        },
                    },
                    "async": False,
                    "server": {"url": f"{server_url}/vapi/webhook"},
                },
            ],
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "keywords": [
                "Yashraj:3",
                "Kupekar:3",
                "Guftagu:2",
                "LangGraph:2",
                "LangChain:2",
                "FastAPI:2",
                "Pinecone:2",
                "Whisper:2",
                "Silero:2",
                "Scaler:2",
                "Boardroom:2",
                "Donna:2",
                "MongoDB:2",
                "RAG:2",
            ],
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "bIHbv24MWmeRgasZH58o",  # "Will" — natural male voice
            "stability": 0.5,
            "similarityBoost": 0.75,
        },
        "firstMessage": (
            "Hey! I represent Yashraj Koo-pay-kar. "
            "I know all about his work, experience, and what he's built — "
            "or I can help you schedule a call with him. What would you like to know?"
        ),
        "serverUrl": f"{server_url}/vapi/webhook",
        "endCallFunctionEnabled": True,
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 600,
        "backgroundSound": "off",
        "backchannelingEnabled": True,
    }


def create_assistant(server_url: str) -> dict:
    config = get_assistant_config(server_url)
    r = httpx.post(
        f"{VAPI_BASE}/assistant",
        headers={
            "Authorization": f"Bearer {settings.vapi_api_key}",
            "Content-Type": "application/json",
        },
        json=config,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def update_assistant(assistant_id: str, server_url: str) -> dict:
    config = get_assistant_config(server_url)
    r = httpx.patch(
        f"{VAPI_BASE}/assistant/{assistant_id}",
        headers={
            "Authorization": f"Bearer {settings.vapi_api_key}",
            "Content-Type": "application/json",
        },
        json=config,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Vapi assistant")
    parser.add_argument(
        "--server-url",
        default="https://your-app.up.railway.app",
        help="Public URL of your backend (Railway, ngrok, etc.)",
    )
    parser.add_argument(
        "--update",
        metavar="ASSISTANT_ID",
        help="Update an existing assistant by ID",
    )
    args = parser.parse_args()

    if not settings.vapi_api_key:
        print("ERROR: Set VAPI_API_KEY in your .env file")
        print("  Get it from: https://dashboard.vapi.ai/account")
        sys.exit(1)

    if args.server_url == "https://your-app.up.railway.app":
        print("WARNING: Using placeholder server URL.")
        print("  Pass --server-url https://your-deployed-url.com\n")

    print(f"Server URL: {args.server_url}")

    if args.update:
        print(f"Updating assistant {args.update}...")
        result = update_assistant(args.update, args.server_url)
        print(f"Updated! Assistant ID: {result['id']}")
    else:
        print("Creating new assistant...")
        result = create_assistant(args.server_url)
        print(f"Created! Assistant ID: {result['id']}")
        print(f"\nSave this in your .env:")
        print(f"  VAPI_ASSISTANT_ID={result['id']}")

    print(f"\nNext steps:")
    print(f"  1. Go to https://dashboard.vapi.ai")
    print(f"  2. Buy a phone number (or use the free web call)")
    print(f"  3. Assign this assistant to the phone number")
    print(f"  4. Call it!")
