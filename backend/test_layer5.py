"""
Layer 5 test: verify Vapi webhook handles function calls correctly.
Run: cd backend && source .venv/bin/activate && python test_layer5.py

Simulates the exact payloads Vapi sends to our webhook.
Does NOT require a Vapi API key — tests the webhook logic locally.
"""

import subprocess
import sys
import time
import json
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


def post_webhook(payload):
    r = httpx.post(f"{BASE_URL}/vapi/webhook", json=payload, timeout=30)
    return r.status_code, r.json()


def test_tool_calls_lookup():
    """Simulate Vapi tool-calls message (current format) — lookup_facts."""
    print("=" * 60)
    print("TEST 1: tool-calls — lookup_facts(skills)")
    print("=" * 60)
    status, body = post_webhook({
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_test_001",
                    "type": "function",
                    "function": {
                        "name": "lookup_facts",
                        "arguments": {"category": "skills"},
                    },
                }
            ],
        }
    })
    assert status == 200, f"Expected 200, got {status}"
    results = body.get("results", [])
    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    assert results[0]["toolCallId"] == "call_test_001"
    assert len(results[0]["result"]) > 50, "Result too short"
    print(f"  toolCallId: {results[0]['toolCallId']}")
    print(f"  Result: {results[0]['result'][:120]}...")
    print("  PASS")


def test_tool_calls_search():
    """Simulate tool-calls — search_knowledge."""
    print("\n" + "=" * 60)
    print("TEST 2: tool-calls — search_knowledge(voice AI)")
    print("=" * 60)
    status, body = post_webhook({
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_test_002",
                    "type": "function",
                    "function": {
                        "name": "search_knowledge",
                        "arguments": {"query": "voice AI projects"},
                    },
                }
            ],
        }
    })
    assert status == 200
    results = body["results"]
    assert len(results) == 1
    assert len(results[0]["result"]) > 50
    print(f"  Result: {results[0]['result'][:120]}...")
    print("  PASS")


def test_tool_calls_calendar():
    """Simulate tool-calls — get_available_slots."""
    print("\n" + "=" * 60)
    print("TEST 3: tool-calls — get_available_slots")
    print("=" * 60)
    status, body = post_webhook({
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_test_003",
                    "type": "function",
                    "function": {
                        "name": "get_available_slots",
                        "arguments": {},
                    },
                }
            ],
        }
    })
    assert status == 200
    results = body["results"]
    assert len(results) == 1
    print(f"  Result: {results[0]['result'][:120]}...")
    print("  PASS")


def test_multiple_tool_calls():
    """Simulate batch tool calls in a single message."""
    print("\n" + "=" * 60)
    print("TEST 4: Batch tool-calls (2 tools at once)")
    print("=" * 60)
    status, body = post_webhook({
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_batch_1",
                    "type": "function",
                    "function": {
                        "name": "lookup_facts",
                        "arguments": {"category": "education"},
                    },
                },
                {
                    "id": "call_batch_2",
                    "type": "function",
                    "function": {
                        "name": "lookup_facts",
                        "arguments": {"category": "experience"},
                    },
                },
            ],
        }
    })
    assert status == 200
    results = body["results"]
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    assert results[0]["toolCallId"] == "call_batch_1"
    assert results[1]["toolCallId"] == "call_batch_2"
    print(f"  Result 1: {results[0]['result'][:80]}...")
    print(f"  Result 2: {results[1]['result'][:80]}...")
    print("  PASS")


def test_legacy_function_call():
    """Simulate legacy function-call format."""
    print("\n" + "=" * 60)
    print("TEST 5: Legacy function-call format")
    print("=" * 60)
    status, body = post_webhook({
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "lookup_facts",
                "parameters": {"category": "education"},
            },
        }
    })
    assert status == 200
    assert "result" in body
    assert len(body["result"]) > 50
    print(f"  Result: {body['result'][:120]}...")
    print("  PASS")


def test_end_of_call():
    """Simulate end-of-call-report."""
    print("\n" + "=" * 60)
    print("TEST 6: end-of-call-report")
    print("=" * 60)
    status, body = post_webhook({
        "message": {
            "type": "end-of-call-report",
            "endedReason": "customer-ended-call",
            "summary": "Caller asked about Yashraj's projects.",
        }
    })
    assert status == 200
    assert body.get("ok") is True
    print("  Acknowledged end-of-call")
    print("  PASS")


def test_unknown_message():
    """Webhook should handle unknown message types gracefully."""
    print("\n" + "=" * 60)
    print("TEST 7: Unknown message type")
    print("=" * 60)
    status, body = post_webhook({
        "message": {
            "type": "status-update",
            "status": "in-progress",
        }
    })
    assert status == 200
    assert body.get("ok") is True
    print("  Handled gracefully")
    print("  PASS")


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

        test_tool_calls_lookup()
        test_tool_calls_search()
        test_tool_calls_calendar()
        test_multiple_tool_calls()
        test_legacy_function_call()
        test_end_of_call()
        test_unknown_message()

        print("\n" + "=" * 60)
        print("All Layer 5 tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    finally:
        server.terminate()
        server.wait()
        print("Server stopped.")
