# AI Persona — System Design & Architecture

> A production AI representative system: chat + voice + calendar booking, grounded in real resume and GitHub data.

---

## 1. System Overview

```mermaid
flowchart LR
    CHAT["Chat UI\n(Next.js)"] -->|POST /chat\nSSE stream| BE
    VOICE["Voice Call\n(Phone)"] -->|Vapi webhook| BE

    BE["FastAPI Backend"] --> CACHE{"Semantic\nCache"}
    CACHE -->|Hit| BE
    CACHE -->|Miss| AGENT["GPT-4o\nAgent"]

    AGENT --> TOOLS["4 Tools:\nlookup_facts\nsearch_knowledge\nget_slots\nbook_meeting"]

    TOOLS --> YAML["persona.yaml"]
    TOOLS --> PINE["Pinecone"]
    TOOLS --> CAL["Cal.com"]

    AGENT -->|response| BE
```

---

## 2. Data Ingestion Pipeline

```mermaid
flowchart LR
    subgraph SOURCES["Data Sources"]
        PDF["Resume PDF<br/>education, experience,<br/>projects, skills"]
        GH["GitHub API<br/>13 repos: READMEs,<br/>descriptions, languages"]
        YML["persona.yaml<br/>why_hire, strengths,<br/>weaknesses"]
    end

    subgraph PROCESSING["Processing"]
        P1["PyPDF2 extract<br/>section-aware chunking<br/>400 tok · 50 overlap"]
        P2["HTTP fetch per repo<br/>2 chunks each<br/>overview + README 3K cap"]
        P3["YAML parse<br/>text chunks"]
    end

    subgraph EMBED["Embedding"]
        E["text-embedding-3-small<br/>1024 dimensions<br/>~46 chunks total"]
    end

    subgraph STORE["Storage"]
        PINE["Pinecone Index<br/>'ai-persona'<br/>batch upsert 100/batch"]
    end

    PDF --> P1
    GH --> P2
    YML --> P3
    P1 -->|"~15 chunks"| E
    P2 -->|"~26 chunks"| E
    P3 -->|"~5 chunks"| E
    E --> PINE
```

### Metadata on each vector

```mermaid
graph LR
    V1["Vector"] -->|"source: github<br/>repo: Medicine-Voice-ai<br/>doc_type: readme"| P["Pinecone"]
    V2["Vector"] -->|"source: resume<br/>section: experience"| P
    V3["Vector"] -->|"source: personal<br/>section: why_hire"| P
```

Metadata enables **filtered searches** — the agent can search only resume, only GitHub, or everything.

---

## 3. Knowledge Retrieval — Hybrid Approach

```mermaid
flowchart TD
    Q["User Question"]
    Q --> LLM["GPT-4o decides<br/>which tool to call"]

    LLM -->|"factual question<br/>skills, education, repos"| LF
    LLM -->|"nuanced question<br/>project details, tradeoffs"| SK

    subgraph FAST["Fast Path · < 5ms"]
        LF["lookup_facts(category)"]
        YAML["persona.yaml<br/>in-memory"]
        LF --> YAML
        YAML -->|"structured YAML dump"| R1["Deterministic<br/>response"]
    end

    subgraph SEMANTIC["Semantic Path · 300-500ms"]
        SK["search_knowledge(query)"]
        EMB2["Embed query<br/>1024-dim vector"]
        SEARCH["Pinecone top-5<br/>cosine similarity"]
        SK --> EMB2 --> SEARCH
        SEARCH -->|"ranked chunks<br/>with scores"| R2["Contextual<br/>response"]
    end
```

**Why hybrid?** Facts (name, education, skills) must be consistent every time — YAML guarantees that. Detailed project explanations need semantic matching across chunked documents — vectors handle that.

---

## 4. Chat Flow — Browser to Response

```mermaid
sequenceDiagram
    participant U as Browser (Next.js)
    participant F as FastAPI Backend
    participant C as Semantic Cache
    participant A as GPT-4o Agent
    participant T as Tools
    participant P as Pinecone / Cal.com

    U->>F: POST /chat {messages}
    Note over F: Middleware: request ID,<br/>rate limit (20/min), CORS

    F->>C: Cache lookup (embed query,<br/>compare cosine similarity)
    alt Cache HIT (sim >= 0.92)
        C-->>F: Cached response + sources
        F-->>U: SSE stream (cached) ~300ms
    else Cache MISS
        C-->>F: No match
        F->>A: Run agent loop

        A->>A: Iteration 1: GPT-4o with tools
        A->>T: tool_call: search_knowledge("query")
        T->>P: Embed → Pinecone vector search
        P-->>T: Top 5 chunks + scores
        T-->>A: Formatted results with sources

        A->>A: Iteration 2: GPT-4o with tool results
        Note over A: No more tools needed → generate answer

        A-->>F: Stream tokens
        F-->>U: SSE: event:token data:"..."
        F-->>U: SSE: event:sources data:[...]
        F-->>U: SSE: event:done

        F->>C: Store in cache (1hr TTL)
        F->>F: Log AgentTrace + Opik
    end
```

### SSE Protocol

```mermaid
sequenceDiagram
    participant S as Server
    participant B as Browser

    S->>B: event: token, data: "Medicine"
    S->>B: event: token, data: " Voice"
    S->>B: event: token, data: " AI is..."
    Note over S,B: ... tokens stream in real-time ...
    S->>B: event: sources, data: [{"tool":"search_knowledge"}]
    S->>B: event: done, data: ""
    Note over B: Render markdown, show source badges,<br/>auto-scroll to bottom
```

---

## 5. Voice Flow — Phone Call to Response

```mermaid
sequenceDiagram
    participant C as Caller
    participant V as Vapi Cloud
    participant D as Deepgram nova-3
    participant G as GPT-4o (Vapi-hosted)
    participant B as FastAPI Backend
    participant T as Tools (persona.yaml / Pinecone / Cal.com)
    participant E as ElevenLabs TTS

    C->>V: Dial phone number
    V->>C: "Hey! I represent Yashraj Koo-pay-kar..."

    C->>V: "What has he built?"
    V->>D: Audio stream
    Note over D: en-IN locale<br/>Keyword boost: Yashraj(5),<br/>Guftagu(5), LangGraph(3)
    D-->>V: "What has he built?"

    V->>G: Transcript + system prompt v4 + voice addendum
    Note over G: Same tools as chat<br/>+ conversational tone rules<br/>+ no URLs spoken<br/>+ IST timezone

    G->>V: tool_call: lookup_facts("github_repos")
    V->>B: POST /vapi/webhook {tool-calls}
    B->>T: Execute lookup_facts
    T-->>B: Repo list from persona.yaml
    B-->>V: {results: [{toolCallId, result}]}
    V->>G: Tool results

    G-->>V: "One of the interesting things he's built<br/>is Medicine Voice AI — it's a fully offline<br/>pharmacy assistant..."

    V->>E: Text chunks (streaming)
    Note over E: Voice: "Will"<br/>Chunk on punctuation<br/>Min 80 chars
    E-->>V: Audio stream
    V-->>C: Caller hears response
```

### Interruption Handling

```mermaid
stateDiagram-v2
    [*] --> Listening
    Listening --> Speaking: Agent responds
    Speaking --> Interrupted: Caller says 2+ words<br/>within 0.3s
    Interrupted --> Backoff: Stop TTS immediately
    Backoff --> Listening: Wait 1.0s
    Speaking --> Listening: Response complete
    Listening --> Silence: No speech for 0.6s
    Silence --> EndpointDetected: Smart endpointing ML
    EndpointDetected --> Speaking: Agent responds
    Listening --> Timeout: 20s silence
    Timeout --> [*]: Disconnect
```

| Feature | Config | Purpose |
|---------|--------|---------|
| Interruption | 2+ words + 0.3s voice | Stop TTS when caller talks over |
| Backoff | 1.0s | Pause before responding to interruption |
| Smart endpointing | 0.6s + ML model | Detect when caller finishes speaking |
| Silence timeout | 20 seconds | Disconnect on prolonged silence |
| Max duration | 10 minutes | Hard limit per call |
| Background denoising | Enabled | Filter ambient noise |
| Backchannel | Enabled | Natural "mm-hmm" acknowledgments |

---

## 6. Calendar Booking Flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as GPT-4o Agent
    participant T as Tools
    participant CAL as Cal.com v2 API

    U->>A: "Can I schedule a call?"
    A->>U: "What days/times work for you?"
    U->>A: "Tomorrow afternoon"

    A->>T: get_available_slots("2026-04-15", "2026-04-15")
    T->>CAL: GET /v2/slots/available<br/>eventTypeId=5337255<br/>eventTypeSlug=30min
    CAL-->>T: UTC timestamps for open slots

    Note over T: Convert UTC → IST (UTC+5:30)<br/>"14:00 IST (UTC: ...T08:30:00Z)"

    T-->>A: Formatted slots in IST
    A->>U: "14:00 IST, 14:30 IST, 15:00 IST..."

    Note over U: Chat: clickable slot buttons<br/>Voice: max 3 options spoken

    U->>A: "2 PM works"
    A->>U: "Name and email?"
    U->>A: "John Smith, john@example.com"
    A->>U: Confirm: "John Smith, john@example.com,<br/>2 PM IST tomorrow?"
    U->>A: "Yes"

    A->>T: book_meeting(name, email, start_time_utc)
    T->>CAL: POST /v2/bookings<br/>{start, eventTypeId, attendee}
    CAL-->>T: {status: "accepted", meetingUrl: "..."}
    T-->>A: Booking confirmed
    A->>U: "Booked! Calendar invite on its way."
```

---

## 7. Semantic Cache

```mermaid
flowchart TD
    Q["Incoming query"]
    Q --> CAL_CHECK{"Calendar query?<br/>schedule, book, slot..."}
    CAL_CHECK -->|"Yes"| SKIP["Skip cache<br/><i>time-sensitive data</i>"]
    CAL_CHECK -->|"No"| EMBED["Embed query<br/>text-embedding-3-small → 1024d"]

    EMBED --> COMPARE["Compare against all<br/>cached query vectors<br/>(cosine similarity)"]

    COMPARE --> HIT{"Best similarity<br/>>= 0.92?"}
    HIT -->|"Yes · CACHE HIT"| RETURN["Return cached response<br/>~300ms · $0.00002"]
    HIT -->|"No · CACHE MISS"| AGENT["Run full agent loop<br/>~5-10s · ~$0.02"]

    AGENT --> STORE["Store in cache"]
    STORE --> DUP{"Near-duplicate?<br/>sim >= 0.98?"}
    DUP -->|"Yes"| SKIP2["Skip store<br/><i>already cached</i>"]
    DUP -->|"No"| SAVE["Save: embedding +<br/>response + sources<br/>TTL: 1 hour"]

    SKIP --> AGENT
```

| Rule | Value | Why |
|------|-------|-----|
| Hit threshold | cosine >= 0.92 | Catches paraphrases, avoids false positives |
| TTL | 1 hour | Balances freshness vs cost savings |
| Max entries | 200 | In-memory dict, bounded |
| Calendar bypass | Keyword detection | Stale slots = bad UX |
| Near-duplicate | sim >= 0.98 skip store | Don't waste space |

---

## 8. Agent Loop — GPT-4o + Function Calling

```mermaid
flowchart TD
    START["messages = system_prompt_v4 +<br/>conversation history"]
    START --> LOOP

    subgraph LOOP["Agent Loop · max 5 iterations"]
        CALL["Call GPT-4o<br/>tools: 4 functions<br/>tool_choice: auto"]
        CALL --> CHECK{"Response has<br/>tool_calls?"}
        CHECK -->|"Yes"| EXEC["Execute tool(s)"]
        EXEC --> APPEND["Append tool results<br/>to messages"]
        APPEND --> CALL
        CHECK -->|"No"| DONE["Final answer ready"]
    end

    DONE --> STREAM["Stream response<br/>token-by-token via SSE"]
    STREAM --> POST["Post-processing:<br/>cache store + AgentTrace + Opik"]
```

### Four Tools

```mermaid
graph LR
    subgraph TOOLS["GPT-4o picks the right tool"]
        T1["lookup_facts(category)<br/><b>persona.yaml</b><br/><i>Facts: skills, education, repos</i><br/>< 5ms"]
        T2["search_knowledge(query)<br/><b>Pinecone vectors</b><br/><i>Nuance: project details, tradeoffs</i><br/>300-500ms"]
        T3["get_available_slots(dates)<br/><b>Cal.com API</b><br/><i>Calendar: open time slots</i><br/>~500ms"]
        T4["book_meeting(name,email,time)<br/><b>Cal.com API</b><br/><i>Booking: create calendar event</i><br/>~800ms"]
    end
```

### System Prompt v4 — Key Rules

```mermaid
mindmap
    root((System Prompt v4))
        Identity
            Engineer who ships production systems
            Not a student listing skills
            Lead with work, not education
        Tone
            Specific and technical
            No filler words
            Banned: passionate, innovative, proficient in
        Grounding
            Only answer from tool results
            If no data, say so
            Never hallucinate
        Links
            Chat: include GitHub/LinkedIn/blog
            Voice: never speak URLs
        Booking
            Confirm name + email + time
            Before calling book_meeting
```

### Prompt Version History

| Version | Change |
|---------|--------|
| v1 | Initial — generic tone, basic routing |
| v2 | Grounding rules, refusal handling, link formatting |
| v3 | Specific over generic, no filler, technical depth |
| v4 | Engineer who ships, not student with skills |

---

## 9. Observability Stack

```mermaid
flowchart TB
    REQ["Every Request"] --> L1 & L2 & L3 & L4

    subgraph L1["Layer 1: Request Logging · structlog"]
        RL["JSON per request<br/>request_id · method · path<br/>status · duration_ms"]
    end

    subgraph L2["Layer 2: Agent Tracing · custom"]
        AT["JSON per agent run<br/>query · prompt_version · cache_hit<br/>iterations · tools · tokens<br/>cost_usd · duration_ms"]
    end

    subgraph L3["Layer 3: Cache Events"]
        CE["JSON per cache op<br/>cache_hit/miss/store<br/>similarity · query · cache_size"]
    end

    subgraph L4["Layer 4: Opik Dashboard · visual"]
        OP["Prompt Library: v1→v2→v3→v4 diff view<br/>Trace waterfall: LLM + tool timeline<br/>Tags: agent, prompt-v4<br/>Cost aggregation over time"]
    end
```

### Prompt Versioning Flow

```mermaid
flowchart LR
    CODE["prompts.py<br/>PROMPT_VERSION = '4'"]
    CODE -->|"logged per request"| LOG["AgentTrace JSON<br/>prompt_version: '4'"]
    CODE -->|"synced on startup"| OPIK["Opik Prompt Library<br/>auto-versions on change"]
    LOG -->|"correlate"| DEBUG["Bad response?<br/>→ check which prompt version"]
    OPIK -->|"visual diff"| DIFF["Compare v3 vs v4<br/>in dashboard"]
```

---

## 10. Deployment Architecture

```mermaid
flowchart TB
    subgraph VERCEL["Vercel"]
        FE["Next.js Frontend<br/>Static + Edge Runtime<br/><br/>Env: NEXT_PUBLIC_API_URL"]
    end

    subgraph RAILWAY["Railway"]
        BE["FastAPI Backend<br/>Docker: python:3.12-slim<br/>gunicorn + 2 uvicorn workers<br/>Port: 8000<br/><br/>Env: OPENAI_API_KEY<br/>PINECONE_API_KEY<br/>CALCOM_API_KEY<br/>VAPI_API_KEY<br/>OPIK_API_KEY<br/>FRONTEND_URL"]
    end

    subgraph MANAGED["Managed Services"]
        PINE["Pinecone<br/>Vector DB"]
        CALCOM["Cal.com<br/>Calendar API"]
        VAPICLOUD["Vapi Cloud<br/>Voice Pipeline"]
        OPIKCLOUD["Opik<br/>Observability"]
    end

    FE -->|"HTTPS"| BE
    BE <-->|"vector search"| PINE
    BE <-->|"slots + bookings"| CALCOM
    VAPICLOUD -->|"tool webhooks"| BE
    BE -->|"traces"| OPIKCLOUD
```

### Docker Build

```mermaid
flowchart LR
    BASE["python:3.12-slim"] --> DEPS["pip install<br/>requirements.txt"]
    DEPS --> COPY["Copy app code"]
    COPY --> RUN["gunicorn app.main:app<br/>-w 2 -k UvicornWorker<br/>--bind 0.0.0.0:8000<br/>--timeout 120"]
```

---

## 11. Technology Decisions

| Decision | Chose | Over | Why |
|----------|-------|------|-----|
| Agent framework | Hand-rolled loop | LangChain / LangGraph | 4 tools, linear flow — framework adds complexity without benefit |
| Knowledge retrieval | Hybrid (YAML + Pinecone) | Pure RAG | Facts must be consistent (YAML). Nuance needs semantic search (Pinecone). |
| Embedding model | text-embedding-3-small (1024d) | ada-002 / 3-large | Cheaper, faster, sufficient for ~50 chunks |
| Vector DB | Pinecone | FAISS / ChromaDB | Managed, no infra to maintain |
| Chat streaming | SSE | WebSocket | One-way stream. Auto-reconnects, simpler client. |
| Voice pipeline | Vapi (managed) | Twilio + custom | Handles real-time STT→LLM→TTS. We just serve tools. |
| STT | Deepgram nova-3 (en-IN) | Whisper API | 54% lower WER, Indian English locale, real-time |
| TTS | ElevenLabs | Google TTS | Natural voice, streaming chunk plan for low latency |
| Calendar | Cal.com v2 | Calendly / Google Calendar | Better API, free tier, direct booking |
| Cache | Semantic (cosine) | Exact string match | Paraphrases hit cache: "Who is Yashraj?" = "Tell me about Yashraj" |
| Observability | structlog + AgentTrace + Opik | Just print() / just Opik | Each layer serves a different audience |
| Server | gunicorn + uvicorn | uvicorn alone | Process management: restart on crash, worker scaling |
| Rate limiting | slowapi (20/min) | nginx / none | Protects OpenAI API key from abuse |
| Prompt versioning | Code constant + Opik | Git alone | Can correlate "bad response → used prompt v3" |
| Frontend | Next.js + shadcn/ui | React SPA | SSR, component library, Vercel zero-config deploy |

---

## 12. Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, middleware, endpoints
│   ├── config.py                  # Pydantic settings from env vars
│   ├── core/
│   │   ├── agent.py               # GPT-4o agent loop (streaming + non-streaming)
│   │   ├── prompts.py             # System prompt v4, versioning, changelog
│   │   └── tools.py               # Tool schemas + execute_tool() dispatcher
│   ├── services/
│   │   ├── knowledge.py           # lookup_facts (YAML) + search_knowledge (Pinecone)
│   │   ├── calendar_client.py     # Cal.com v2: get_slots + book_meeting
│   │   ├── cache.py               # Semantic cache (cosine similarity, in-memory)
│   │   ├── embeddings.py          # OpenAI embedding wrapper
│   │   ├── pinecone_client.py     # Pinecone init + search
│   │   └── observability.py       # AgentTrace, LLMTrace, ToolTrace
│   ├── routers/
│   │   ├── chat.py                # POST /chat (SSE streaming, rate-limited)
│   │   └── vapi.py                # POST /vapi/webhook (voice tool dispatch)
│   ├── middleware/
│   │   └── logging.py             # Request ID + duration logging
│   ├── ingestion/
│   │   ├── ingest.py              # CLI: orchestrate all data loading
│   │   ├── resume_loader.py       # PDF → section-aware chunks
│   │   └── github_loader.py       # GitHub API → repo chunks
│   └── data/
│       ├── persona.yaml           # Structured facts (deterministic)
│       └── resume.pdf             # Resume document
├── setup_vapi.py                  # Create/update Vapi assistant config
├── evals.py                       # RAGAS + custom eval suite
├── Dockerfile                     # Production image
├── requirements.txt               # Production deps
└── requirements-dev.txt           # Dev/eval deps

frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx               # Chat UI: SSE, slot picker, source badges
│   │   ├── layout.tsx             # Root layout
│   │   └── globals.css            # Styles
│   ├── components/ui/             # shadcn/ui: card, badge, button, input
│   └── lib/utils.ts               # Utilities
└── next.config.ts
```

---

## 13. API Endpoints

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `POST` | `/chat` | Chat with SSE streaming | Rate-limited (20/min) |
| `POST` | `/vapi/webhook` | Vapi voice tool dispatch | Vapi server |
| `GET` | `/health` | Liveness check | None |
| `GET` | `/cache/stats` | Cache metrics | None |
| `GET` | `/prompt/version` | Prompt version + changelog | None |
| `GET` | `/resume` | Download resume PDF | None |

---

## 14. Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | GPT-4o + embeddings |
| `PINECONE_API_KEY` | Yes | Vector storage |
| `CALCOM_API_KEY` | For booking | Calendar integration |
| `CALCOM_EVENT_TYPE_ID` | For booking | Event type to book |
| `VAPI_API_KEY` | For voice | Voice assistant management |
| `OPIK_API_KEY` | For observability | Visual trace dashboard |
| `OPIK_WORKSPACE` | For observability | Opik workspace name |
| `FRONTEND_URL` | Production | CORS whitelist |
| `API_BASE_URL` | Production | Resume download link |
