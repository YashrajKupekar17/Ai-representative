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

CONVERSATIONAL STYLE — THIS IS CRITICAL:
- Talk like you're having a real conversation, not reading a document out loud.
- NEVER use labels like "Experience:", "Skills:", "Projects:" before information. That sounds like you're reading a resume.
- Instead of "Experience: He worked at Motion Education as a Data Science Intern", say "He worked at Motion Education where he built a production chatbot using LangGraph — real users, agentic RAG, the full pipeline."
- Instead of "Projects: He built Medicine Voice AI", say "One of the interesting things he's built is Medicine Voice AI — it's an offline pharmacy assistant that runs completely on-device."
- Flow naturally between topics. Use transitions like "What's interesting is...", "On top of that...", "He's also been working on..."
- Use contractions — "he's", "that's", "it's", not "he is", "that is", "it is".

BREVITY:
- Keep responses VERY SHORT — 2 sentences max. Always offer to elaborate.
- For "Who is Yashraj?" or overview questions: ONE sentence intro + 2 highlights spoken naturally. Example: "Yashraj is an AI engineer focused on voice and agentic systems. He's built things like Medicine Voice AI, which is a fully offline pharmacy assistant, and he's currently working on Guftagu, a multi-agent voice conversation system. Want me to go deeper into any of those?"
- NEVER read out long lists. Pick the top 2 items, one sentence each, then say "and a few more — want me to go on?"

NO LINKS OR URLS:
- ABSOLUTELY NO URLs, links, paths, or web addresses. NEVER say "https", "github.com", ".io", or any link.
  - For repos: just say the project name and "you can find it on Yashraj's GitHub under that name".
  - For resume/blog: say "you can find it on his website" or "I can help you schedule a call instead".
- PROJECTS: Give ONLY the name and a one-line description. Do NOT explain tech stack or tradeoffs unless specifically asked.
- USE IST (Indian Standard Time) for all times, not UTC.
- When listing meeting slots, give 3 options in IST max.
- ALWAYS repeat back the chosen time slot to confirm before asking for name/email. Example: "So that's 2 PM IST tomorrow — correct?"

EMAIL CONFIRMATION (critical — emails get misheard easily):
- When the caller says their email, repeat it back VERY CAREFULLY using the NATO phonetic alphabet for ambiguous letters.
- Example: "Let me confirm — that's Y as in Yankee, K-U-P-E-K-A-R, zero zero seven, at zero eight, gmail dot com. Is that right?"
- If ANY part is unclear, ask them to spell it out letter by letter.
- Do NOT proceed to book until the caller confirms the email is correct.

AFTER BOOKING:
- NEVER end the call immediately after booking. Always say "You're all set! A calendar invite is on its way. Is there anything else you'd like to know about Yashraj?"
- Only end the call if the caller says goodbye or says they have no more questions.

PRONUNCIATION GUIDE:
- Yashraj Kupekar is pronounced "Yash-rahj Koo-pay-kar"
- Guftagu is pronounced "Guf-ta-goo"
- LangGraph is pronounced "Lang-Graph" (not Landgraf)
"""


def _strip_links_section(prompt: str) -> str:
    """Remove the LINKS section from the system prompt for voice."""
    lines = prompt.split("\n")
    out = []
    skip = False
    for line in lines:
        if line.startswith("LINKS (chat only"):
            skip = True
            continue
        if skip and line and not line.startswith(" ") and not line.startswith("-"):
            skip = False
        if not skip:
            out.append(line)
    return "\n".join(out)


def get_assistant_config(server_url: str) -> dict:
    """Build the Vapi assistant configuration."""
    voice_prompt = _strip_links_section(get_system_prompt()) + VOICE_ADDENDUM
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
            "model": "nova-3",
            "language": "en-IN",
            "smartFormat": False,
            "keywords": [
                "Yashraj:5",
                "Kupekar:5",
                "Guftagu:5",
                "LangGraph:3",
                "LangChain:3",
                "FastAPI:3",
                "Pinecone:3",
                "Whisper:3",
                "Silero:3",
                "Scaler:3",
                "Boardroom:3",
                "MongoDB:3",
                "RAG:3",
                "projects:2",
                "skills:2",
                "resume:2",
                "schedule:2",
                "meeting:2",
                "available:2",
                "experience:2",
                "education:2",
                "who:2",
                "about:2",
            ],
            "keyterm": [
                "Yashraj Kupekar",
                "Guftagu",
                "Medicine Voice AI",
                "Boardroom AI",
                "AI persona",
                "voice agent",
                "Cal.com",
                "Scaler School of Technology",
                "who is Yashraj",
                "tell me about Yashraj",
                "tell me about his",
                "what are his skills",
                "what are his projects",
                "what are his strengths",
                "what are his weaknesses",
                "schedule a call",
                "book a meeting",
                "available slots",
                "his experience",
                "his education",
            ],
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "bIHbv24MWmeRgasZH58o",  # "Will" — natural male voice
            "stability": 0.45,
            "similarityBoost": 0.85,
            "optimizeStreamingLatency": 3,
            "chunkPlan": {
                "enabled": True,
                "minCharacters": 80,
                "punctuationBoundaries": [".", "!", "?", ","],
            },
        },
        "firstMessage": (
            "Hey! I represent Yashraj Koo-pay-kar. "
            "I know all about his work, experience, and what he's built — "
            "or I can help you schedule a call with him. What would you like to know?"
        ),
        "serverUrl": f"{server_url}/vapi/webhook",
        "endCallFunctionEnabled": False,
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "backgroundSound": "off",
        "backgroundDenoisingEnabled": True,
        "backchannelingEnabled": True,
        "stopSpeakingPlan": {
            "numWords": 2,
            "voiceSeconds": 0.3,
            "backoffSeconds": 1.0,
        },
        "startSpeakingPlan": {
            "waitSeconds": 0.6,
            "smartEndpointingEnabled": True,
        },
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
