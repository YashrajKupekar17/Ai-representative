"""
Layer 4 test: verify FastAPI chat API with SSE streaming.
Run: cd backend && source .venv/bin/activate && python test_layer4.py

Starts the server automatically, runs tests, then shuts down.
"""

import subprocess
import sys
import time
import json
import httpx


BASE_URL = "http://localhost:8000"


def wait_for_server(timeout=10):
    """Wait until the server is ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                return True
        except httpx.ConnectError:
            time.sleep(0.5)
    return False


def test_health():
    print("=" * 60)
    print("TEST 1: Health Endpoint")
    print("=" * 60)
    r = httpx.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert r.json()["status"] == "ok"
    print("  GET /health → 200 {'status': 'ok'}")
    print("  PASS")


def test_request_id():
    print("\n" + "=" * 60)
    print("TEST 2: Request ID Header")
    print("=" * 60)
    r = httpx.get(f"{BASE_URL}/health")
    rid = r.headers.get("x-request-id")
    assert rid, "Missing x-request-id header"
    print(f"  x-request-id: {rid}")
    print("  PASS")


def test_cors():
    print("\n" + "=" * 60)
    print("TEST 3: CORS Headers")
    print("=" * 60)
    r = httpx.options(
        f"{BASE_URL}/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    allow_origin = r.headers.get("access-control-allow-origin")
    assert allow_origin, "Missing access-control-allow-origin"
    print(f"  access-control-allow-origin: {allow_origin}")
    print("  PASS")


def test_invalid_body():
    print("\n" + "=" * 60)
    print("TEST 4: Invalid Request Body → 422")
    print("=" * 60)
    r = httpx.post(f"{BASE_URL}/chat", json={"bad": "data"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    print(f"  POST /chat with bad body → {r.status_code}")
    print("  PASS")


def collect_sse(messages, timeout=30):
    """Send a chat request and collect all SSE events."""
    tokens = []
    sources = []
    with httpx.stream(
        "POST",
        f"{BASE_URL}/chat",
        json={"messages": messages},
        timeout=timeout,
    ) as r:
        event_type = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
                if event_type == "token":
                    tokens.append(data)
                elif event_type == "sources":
                    sources = json.loads(data)
                elif event_type == "done":
                    break
    return "".join(tokens), sources


def test_streaming_factual():
    print("\n" + "=" * 60)
    print("TEST 5: SSE Streaming — Factual Query (lookup_facts)")
    print("=" * 60)
    text, sources = collect_sse([{"role": "user", "content": "What are Yashraj's skills?"}])
    assert len(text) > 50, f"Response too short: {len(text)} chars"
    tool_names = [s["tool"] for s in sources]
    print(f"  Response: {text[:120]}...")
    print(f"  Sources: {tool_names}")
    assert "lookup_facts" in tool_names, "Expected lookup_facts to be called"
    print("  PASS")


def test_streaming_semantic():
    print("\n" + "=" * 60)
    print("TEST 6: SSE Streaming — Deep Query (search_knowledge)")
    print("=" * 60)
    text, sources = collect_sse([
        {"role": "user", "content": "Tell me about Yashraj's voice AI experience and technical tradeoffs"}
    ])
    assert len(text) > 50, f"Response too short: {len(text)} chars"
    tool_names = [s["tool"] for s in sources]
    print(f"  Response: {text[:120]}...")
    print(f"  Sources: {tool_names}")
    assert "search_knowledge" in tool_names, "Expected search_knowledge to be called"
    print("  PASS")


def test_multi_turn():
    print("\n" + "=" * 60)
    print("TEST 7: Multi-turn Conversation")
    print("=" * 60)
    text, sources = collect_sse([
        {"role": "user", "content": "What projects has Yashraj built?"},
        {"role": "assistant", "content": "He has built Dinner Talk, Medicine Assistant, and more."},
        {"role": "user", "content": "Tell me more about the Medicine Assistant"},
    ])
    assert len(text) > 50, f"Response too short: {len(text)} chars"
    print(f"  Response: {text[:120]}...")
    print(f"  Sources: {[s['tool'] for s in sources]}")
    print("  PASS")


def test_edge_redirect():
    print("\n" + "=" * 60)
    print("TEST 8: Off-topic Redirect")
    print("=" * 60)
    text, sources = collect_sse([{"role": "user", "content": "What's the weather today?"}])
    assert len(text) > 20, f"Response too short: {len(text)} chars"
    print(f"  Response: {text[:150]}...")
    print("  PASS")


if __name__ == "__main__":
    # Start server
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

        test_health()
        test_request_id()
        test_cors()
        test_invalid_body()
        test_streaming_factual()
        test_streaming_semantic()
        test_multi_turn()
        test_edge_redirect()

        print("\n" + "=" * 60)
        print("All Layer 4 tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    finally:
        server.terminate()
        server.wait()
        print("Server stopped.")
