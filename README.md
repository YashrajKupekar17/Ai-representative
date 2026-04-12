# AI Persona — Yashraj Kupekar

A production-grade AI representative that answers questions about me via **chat** and **voice**, grounded in my resume, GitHub repos, and structured profile. Includes real-time calendar booking via Cal.com.

## Live Demo

- **Chat**: [Coming soon — Vercel deploy]
- **Voice**: Call **+1 (475) 222-2335** (Vapi-powered, ElevenLabs TTS)
- **API**: [Coming soon — Railway deploy]

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────────┐
│  Next.js UI  │────▶│  FastAPI     │────▶│  GPT-4o Agent        │
│  (Vercel)    │ SSE │  (Railway)   │     │  + Function Calling  │
└─────────────┘     └──────┬───────┘     └──────────┬───────────┘
                           │                        │
┌─────────────┐     ┌──────┴───────┐     ┌──────────┴───────────┐
│  Vapi Voice  │────▶│  /vapi/      │     │  4 Tools:            │
│  (Phone/Web) │ POST│  webhook     │     │  - lookup_facts      │
└─────────────┘     └──────────────┘     │  - search_knowledge   │
                                         │  - get_available_slots│
                                         │  - book_meeting       │
                                         └──────────┬───────────┘
                                                    │
                              ┌──────────────┬──────┴──────┐
                              │              │             │
                        ┌─────┴─────┐  ┌─────┴────┐ ┌─────┴─────┐
                        │ Pinecone  │  │ persona  │ │ Cal.com   │
                        │ (vectors) │  │ .yaml    │ │ (calendar)│
                        └───────────┘  └──────────┘ └───────────┘
```

**Key design decision**: Same agent pipeline for chat and voice. Vapi handles STT/TTS/telephony, our webhook executes tool calls — identical knowledge base, identical answers.

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | GPT-4o + function calling | Agent reasoning + tool routing |
| Knowledge | Pinecone + persona.yaml | Hybrid retrieval (semantic + structured) |
| Embeddings | text-embedding-3-small (1024d) | Resume + GitHub → vectors |
| Backend | FastAPI + SSE | Chat API with streaming |
| Voice | Vapi + ElevenLabs + Deepgram | Phone/web voice agent |
| Calendar | Cal.com v2 API | Real-time slot fetching + booking |
| Frontend | Next.js + shadcn/ui | Streaming chat with slot picker |

## Project Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── agent.py          # GPT-4o agent with tool-call loop
│   │   ├── prompts.py        # System prompt (chat + voice addendum)
│   │   └── tools.py          # Tool schemas + execution dispatch
│   ├── services/
│   │   ├── knowledge.py      # Hybrid retrieval: YAML lookup + Pinecone search
│   │   ├── calendar_client.py # Cal.com v2 integration
│   │   ├── embeddings.py     # OpenAI embedding helper
│   │   └── pinecone_client.py # Vector upsert + search
│   ├── routers/
│   │   ├── chat.py           # POST /chat (SSE streaming)
│   │   └── vapi.py           # POST /vapi/webhook (voice tool calls)
│   ├── ingestion/
│   │   ├── ingest.py         # CLI: load resume + GitHub + persona → Pinecone
│   │   ├── resume_loader.py  # PDF → section-aware chunks
│   │   └── github_loader.py  # GitHub API → repo overview + README chunks
│   ├── data/
│   │   └── persona.yaml      # Structured facts (education, skills, repos, etc.)
│   └── main.py               # FastAPI app entry point
├── setup_vapi.py              # Create/update Vapi assistant via API
├── evals.py                   # Evaluation suite (6 categories, 16 tests)
├── test_layer[1-5].py         # Layer-by-layer test scripts
└── requirements.txt
frontend/
├── src/app/
│   ├── page.tsx               # Chat UI: SSE streaming, slot picker, markdown
│   ├── layout.tsx             # Root layout
│   └── globals.css            # Tailwind + shadcn theme
└── package.json
```

## Setup

### Prerequisites
- Python 3.9+, Node.js 18+
- API keys: OpenAI, Pinecone, Cal.com, Vapi (optional)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in API keys
python -m app.ingestion.ingest  # load knowledge base
uvicorn app.main:app --port 8000
```

### Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Voice Agent
```bash
# Add VAPI_API_KEY to backend/.env, then:
cd backend
python setup_vapi.py --server-url https://your-public-url.com
# Use ngrok for local testing: ngrok http 8000
```

## Evals

```bash
cd backend && python evals.py
```

| Category | Tests | Pass Rate |
|----------|-------|-----------|
| Groundedness | 4 | 100% |
| Tool Routing | 3 | 100% |
| Hallucination | 2 | 100% |
| Refusal | 3 | 67% |
| Retrieval Quality | 3 | 100% |
| Calendar Flow | 1 | 100% |
| **Total** | **16** | **94%** |

## Design Decisions

1. **Hybrid knowledge** — YAML for deterministic facts (skills, repos), Pinecone for semantic search (project details, experience depth). Ensures consistent answers for direct questions while supporting nuanced queries.

2. **OpenAI function calling over LangGraph** — Single agent + 4 tools is simpler, faster, and sufficient. No state machine needed for this use case.

3. **Unified pipeline for chat + voice** — Same tools, same knowledge, same prompt base. Voice gets an addendum for brevity and no URLs. Zero consistency drift.

4. **Section-aware resume chunking** — Splits by headers, not blind token windows. Each chunk knows its section (education, experience, projects), improving retrieval precision.

5. **Deepgram keyword boosting** — Custom vocabulary weights for "Yashraj", "Kupekar", project names, and tech terms. Significantly improves STT accuracy for domain-specific words.
