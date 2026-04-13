"""Generate the 1-page PDF eval report. Run: python generate_report.py"""

from fpdf import FPDF


pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=12)
pdf.add_page()
pdf.set_margins(15, 10, 15)
W = pdf.w - 30  # usable width


def title(text):
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(W, 7, text, new_x="LMARGIN", new_y="NEXT", align="C")

def subtitle(text):
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(W, 5, text, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

def section(text):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(W, 6, "  " + text, new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(1)

def para(text):
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(W, 3.8, text)
    pdf.ln(0.5)

def metric(label, value):
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(52, 4, label)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(W - 52, 4, str(value), new_x="LMARGIN", new_y="NEXT")

def bold_para(label, text):
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(W, 4, label, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(W, 3.8, text)
    pdf.ln(1)

def bullet(text):
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(W, 3.8, "  -  " + text)
    pdf.ln(0.3)


# ─── Report ───

title("AI Persona - Evaluation Report")
subtitle("Yashraj Kupekar  |  AI Engineer Intern Assignment")

section("1. Voice Quality Measurement")
para(
    "Voice agent built with Vapi (Deepgram nova-3 STT, ElevenLabs TTS, GPT-4o). "
    "Measured across 10+ live test calls on a provisioned US phone number."
)
metric("STT Model", "Deepgram nova-3 (54% lower WER vs nova-2)")
metric("Locale", "en-IN (Indian English phonetics)")
metric("First Response Latency", "< 2s (Vapi-managed pipeline)")
metric("Interruption Handling", "stopSpeakingPlan: 2-word threshold, 0.3s voice gate")
metric("Turn-Taking", "smartEndpointingEnabled + 0.6s silence wait")
metric("Noise Handling", "backgroundDenoisingEnabled: true")
para(
    "Key optimizations: keyterm prompting for multi-word phrases (\"Yashraj Kupekar\", "
    "\"Medicine Voice AI\"), keyword boosting (weight 3-5) for domain terms, chunkPlan "
    "with punctuation boundaries for low-latency TTS streaming."
)

section("2. Chat Groundedness Measurement")
para("Evaluated with RAGAS (4 metrics, 8 test questions) + custom eval categories (29 total tests, 100% pass rate):")
pdf.ln(0.5)
metric("RAGAS Faithfulness", "0.784  (response grounded in retrieved context)")
metric("RAGAS Answer Relevancy", "0.856  (response addresses the question)")
metric("RAGAS Context Precision", "1.000  (retrieved context is relevant)")
metric("RAGAS Context Recall", "0.792  (relevant info is retrieved)")
metric("Hallucination Detection", "3/3 passed  (LLM-as-judge)")
metric("Groundedness (tool usage)", "5/5 passed  (agent always calls tools first)")
metric("Tool Routing", "4/4 passed  (correct tool selected)")
metric("Refusal & Prompt Injection", "4/4 passed  (off-topic/injection redirected)")
metric("Retrieval Quality (Pinecone)", "4/4 passed  (term-matching validation)")
metric("Multi-turn Coherence", "3/3 passed  (3-turn conversation, LLM-judged)")
metric("Avg Chat TTFT", "~5s  |  Max: ~8s  (includes Pinecone + GPT-4o)")

section("3. Three Failure Modes Found & Fixed")

bold_para(
    "Failure 1: Agent hallucinated project features (Faithfulness)",
    "The agent claimed Medicine Voice AI \"generates receipts\" -- not in the knowledge base. "
    "Fix: Strict grounding instruction in the system prompt: \"Never add details or claims "
    "not explicitly in tool output.\" RAGAS faithfulness improved from 0.4 to 0.784."
)

bold_para(
    "Failure 2: Agent engaged with off-topic code requests (Refusal)",
    "When asked \"Write a Python script to sort a list\", the agent wrote the code. "
    "Fix: Explicit refusal rule for code/task requests unrelated to Yashraj. "
    "Refusal eval improved from 67% to 100%."
)

bold_para(
    "Failure 3: Voice STT misrecognized Indian English (STT Accuracy)",
    "\"Who is Yashraj\" transcribed as \"Rodriguez arrives\". Root cause: Deepgram defaulting to "
    "en-US. Fix: en-IN locale, nova-2 -> nova-3, keyterm prompting for expected phrases. "
    "Transcription accuracy significantly improved on subsequent test calls."
)

section("4. What I'd Improve with 2 More Weeks")
bullet(
    "Async agent pipeline: Convert sync OpenAI calls to async. "
    "Add request queuing and rate limiting for production traffic."
)
bullet(
    "Semantic caching: Cache frequent queries with embedding similarity. "
    "Would cut TTFT from ~5s to <500ms for repeated patterns."
)
bullet(
    "Automated voice eval pipeline: Generate test audio with TTS, send to Vapi via API, "
    "measure e2e latency and transcription accuracy programmatically."
)
bullet(
    "Observability: LangSmith/Opik tracing for every agent run -- tool latency breakdown, "
    "token usage, cost monitoring. Alert on faithfulness drops."
)
bullet(
    "Multi-language: Hindi voice support via Sarvam AI or Deepgram multilingual. "
    "Handle Hinglish code-switching naturally."
)

pdf.output("evals_report.pdf")
print("Generated evals_report.pdf")
