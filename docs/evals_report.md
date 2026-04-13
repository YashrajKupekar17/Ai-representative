# Evaluation Report

**Yashraj Kupekar** | AI Persona | April 2026

---

## Voice Quality

| Metric | Method | Result |
|--------|--------|--------|
| Latency (TTFT) | Timed across 4 query types | Avg 5.1s, Max 8.2s |
| STT Accuracy | Deepgram nova-3, en-IN, keyword boosting (Yashraj:5, Guftagu:5) | Domain terms recognized after tuning |
| Task Completion | E2E booking flow: schedule intent → slot fetch → book | 100% |

## Chat Groundedness

| Metric | Method | Result |
|--------|--------|--------|
| Hallucination | 3 trick questions (fake PhD, fake FAANG, fake awards) + LLM judge | 0% |
| Groundedness | 5 queries — every response must trace to a tool call | 100% |
| RAGAS Faithfulness | 8 Q&A pairs, GPT-4o-mini judge | 0.78 |
| RAGAS Relevancy | Response answers the actual question | 0.86 |
| RAGAS Context Precision | Retrieved chunks are relevant | 1.00 |
| RAGAS Context Recall | Context contains enough info to answer | 0.79 |

## Three Failures and Fixes

**1. Robot voice — reading a resume out loud.** Agent said *"Experience: He worked at... Skills: Python, C++..."* Sounded like a document, not a person. Fixed by adding conversational style rules to the voice prompt — banned labels, enforced contractions, capped at 2 sentences, added natural transition examples.

**2. Prompt iteration blind spots.** Went through 4 prompt versions. Each fix broke something else, no way to trace which version caused which regression. Fixed by logging `prompt_version` per request and syncing prompts to Opik's Prompt Library — now every trace shows which version generated it, and I can diff v3 vs v4 in the dashboard.

**3. LangGraph latency overhead.** TTFT was ~12s. Profiled and found LangGraph's state serialization and graph traversal were the bottleneck — overkill for a linear 4-tool pipeline. Replaced with a 50-line hand-rolled loop. Added semantic cache (cosine sim >= 0.92) for paraphrased queries. TTFT dropped to ~5s, cache hits to ~300ms.

## What I'd Improve Next

- **Multilingual voice** — real callers code-switch Hindi/English mid-sentence. Dealt with this in Guftagu (Sarvam AI for Indic), know the hard problems: codeswitching, accents, unnatural Indic TTS.
- **Cost optimization** — ~$0.02/query is fine for demo, not for scale. Need to experiment with GPT-4o-mini for simple routing, persistent Redis cache, pre-computed answers for top 10 queries.
- **Conversation character** — agent is functional but still feels like AI. Need to work on personality, humor, natural topic transitions, shorter turns with follow-up suggestions.
- **Personalized callers** — recognize returning callers, skip intro. Admin mode from my number for schedule changes.
- **Evals in CI** — run core tests on every PR that touches prompts. Block merge if faithfulness drops below 0.75.
