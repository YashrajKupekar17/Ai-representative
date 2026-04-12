"""
Evaluation suite for the AI Persona.
Run: cd backend && source .venv/bin/activate && python evals.py

Tests:
  1. Groundedness — does the agent use tools instead of making things up?
  2. Retrieval quality — are search results relevant?
  3. Hallucination — does the agent invent facts?
  4. Tool routing — does it pick the right tool?
  5. Refusal — does it refuse off-topic questions?
  6. Calendar flow — does booking work end-to-end?

Outputs a JSON report to evals_report.json.
"""

import json
import subprocess
import sys
import time
import httpx

BASE_URL = "http://localhost:8000"


def wait_for_server(timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except httpx.ConnectError:
            time.sleep(0.5)
    return False


def chat(messages: list[dict], timeout=30) -> dict:
    """Send a chat request and collect the full response + sources."""
    tokens = []
    sources = []
    with httpx.stream(
        "POST",
        f"{BASE_URL}/chat",
        json={"messages": messages},
        timeout=timeout,
    ) as r:
        event_type = ""
        for line in r.iter_lines():
            line = line.strip()
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                raw = line[5:]
                data = raw[1:] if raw.startswith(" ") else raw
                if event_type == "token":
                    tokens.append(data if data else "\n")
                elif event_type == "sources":
                    try:
                        sources = json.loads(data)
                    except json.JSONDecodeError:
                        pass
    return {"text": "".join(tokens), "sources": sources}


def tool_names(sources: list[dict]) -> list[str]:
    return [s["tool"] for s in sources]


# ─── Eval cases ───


def eval_groundedness():
    """Agent should call tools, not answer from its own knowledge."""
    cases = [
        {"q": "Who is Yashraj?", "expect_tool": True},
        {"q": "What are his skills?", "expect_tool": True},
        {"q": "Tell me about his projects", "expect_tool": True},
        {"q": "What is his education?", "expect_tool": True},
    ]
    results = []
    for c in cases:
        resp = chat([{"role": "user", "content": c["q"]}])
        used_tool = len(resp["sources"]) > 0
        passed = used_tool == c["expect_tool"]
        results.append({
            "question": c["q"],
            "used_tool": used_tool,
            "tools": tool_names(resp["sources"]),
            "passed": passed,
        })
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {c['q']} → tools: {tool_names(resp['sources'])}")
    return results


def eval_tool_routing():
    """Agent should pick the right tool for each question type."""
    cases = [
        {"q": "What are Yashraj's skills?", "expect": "lookup_facts"},
        {"q": "Tell me about his voice AI experience in detail", "expect": "search_knowledge"},
        {"q": "Is Yashraj available for a call tomorrow?", "expect": "get_available_slots"},
    ]
    results = []
    for c in cases:
        resp = chat([{"role": "user", "content": c["q"]}])
        tools = tool_names(resp["sources"])
        passed = c["expect"] in tools
        results.append({
            "question": c["q"],
            "expected_tool": c["expect"],
            "actual_tools": tools,
            "passed": passed,
        })
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {c['q']} → expected {c['expect']}, got {tools}")
    return results


def eval_hallucination():
    """Agent should not invent facts not in the knowledge base."""
    cases = [
        {
            "q": "What is Yashraj's PhD thesis about?",
            "should_not_contain": ["PhD", "thesis", "dissertation"],
            "description": "Yashraj has no PhD — should not claim one",
        },
        {
            "q": "Which company does Yashraj work at currently?",
            "should_not_contain": ["Google", "Meta", "Amazon", "Microsoft"],
            "description": "Should not invent a current employer",
        },
    ]
    results = []
    for c in cases:
        resp = chat([{"role": "user", "content": c["q"]}])
        text_lower = resp["text"].lower()
        # If the agent refuses ("I don't have"), that's correct — not a hallucination
        is_refusal = any(p in text_lower for p in ["i don't have", "no information", "isn't available"])
        found_bad = [w for w in c["should_not_contain"] if w.lower() in text_lower]
        passed = is_refusal or len(found_bad) == 0
        results.append({
            "question": c["q"],
            "description": c["description"],
            "flagged_words": found_bad,
            "passed": passed,
            "response_snippet": resp["text"][:200],
        })
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {c['description']} → flagged: {found_bad}")
    return results


def eval_refusal():
    """Agent should refuse or redirect off-topic questions."""
    cases = [
        "What's the weather today?",
        "Write me a Python script to sort a list",
        "Who is the president of the United States?",
    ]
    results = []
    for q in cases:
        resp = chat([{"role": "user", "content": q}])
        text_lower = resp["text"].lower()
        redirected = any(
            phrase in text_lower
            for phrase in ["yashraj", "his work", "his projects", "about him", "i can tell you"]
        )
        results.append({
            "question": q,
            "redirected": redirected,
            "passed": redirected,
            "response_snippet": resp["text"][:200],
        })
        status = "PASS" if redirected else "FAIL"
        print(f"  [{status}] '{q}' → redirected: {redirected}")
    return results


def eval_retrieval_quality():
    """Search results should be relevant to the query."""
    from app.services.knowledge import search_knowledge

    cases = [
        {"q": "voice AI experience", "expect_in_result": ["voice", "whisper", "vad", "medicine", "guftagu"]},
        {"q": "education background", "expect_in_result": ["scaler", "bachelor", "computer science"]},
        {"q": "LangGraph projects", "expect_in_result": ["langgraph", "agent", "guftagu"]},
    ]
    results = []
    for c in cases:
        result = search_knowledge(c["q"])
        result_lower = result.lower()
        found = [w for w in c["expect_in_result"] if w in result_lower]
        relevance = len(found) / len(c["expect_in_result"])
        passed = relevance >= 0.5
        results.append({
            "query": c["q"],
            "expected_terms": c["expect_in_result"],
            "found_terms": found,
            "relevance_score": round(relevance, 2),
            "passed": passed,
        })
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] '{c['q']}' → relevance: {relevance:.0%} ({found})")
    return results


def eval_calendar_flow():
    """Test the full booking flow via chat."""
    messages = [
        {"role": "user", "content": "Can I schedule a call with Yashraj?"},
    ]
    resp1 = chat(messages)
    messages.append({"role": "assistant", "content": resp1["text"]})

    messages.append({"role": "user", "content": "tomorrow"})
    resp2 = chat(messages)
    has_slots = "get_available_slots" in tool_names(resp2["sources"])

    passed = has_slots
    print(f"  [{'PASS' if passed else 'FAIL'}] Calendar flow → fetched slots: {has_slots}")
    return [{
        "step": "fetch_slots",
        "passed": has_slots,
        "tools_used": tool_names(resp2["sources"]),
    }]


# ─── Main ───


if __name__ == "__main__":
    print("Starting server...")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server():
            print("ERROR: Server failed to start")
            server.terminate()
            sys.exit(1)
        print("Server ready.\n")

        report = {}

        print("=" * 50)
        print("EVAL 1: Groundedness (does it use tools?)")
        print("=" * 50)
        report["groundedness"] = eval_groundedness()

        print(f"\n{'=' * 50}")
        print("EVAL 2: Tool Routing (right tool for the job?)")
        print("=" * 50)
        report["tool_routing"] = eval_tool_routing()

        print(f"\n{'=' * 50}")
        print("EVAL 3: Hallucination (inventing facts?)")
        print("=" * 50)
        report["hallucination"] = eval_hallucination()

        print(f"\n{'=' * 50}")
        print("EVAL 4: Refusal (off-topic redirect?)")
        print("=" * 50)
        report["refusal"] = eval_refusal()

        print(f"\n{'=' * 50}")
        print("EVAL 5: Retrieval Quality (relevant results?)")
        print("=" * 50)
        report["retrieval_quality"] = eval_retrieval_quality()

        print(f"\n{'=' * 50}")
        print("EVAL 6: Calendar Flow (booking works?)")
        print("=" * 50)
        report["calendar_flow"] = eval_calendar_flow()

        # Summary
        total = 0
        passed = 0
        for category, cases in report.items():
            for c in cases:
                total += 1
                if c["passed"]:
                    passed += 1

        print(f"\n{'=' * 50}")
        print(f"SUMMARY: {passed}/{total} passed ({passed/total:.0%})")
        print("=" * 50)

        report["summary"] = {
            "total": total,
            "passed": passed,
            "score": round(passed / total, 2),
        }

        with open("evals_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to evals_report.json")

    finally:
        server.terminate()
        server.wait()
        print("Server stopped.")
