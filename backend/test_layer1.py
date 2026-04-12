"""
Layer 1 test: verify knowledge base works.
Run: cd backend && source .venv/bin/activate && python test_layer1.py
"""

from app.services.knowledge import lookup_facts, search_knowledge


def test_lookup():
    """Test structured YAML lookups."""
    print("=" * 60)
    print("TEST: Structured Fact Lookups (persona.yaml)")
    print("=" * 60)

    categories = ["education", "skills", "github_repos", "why_hire", "weaknesses"]
    for cat in categories:
        print(f"\n--- lookup_facts('{cat}') ---")
        result = lookup_facts(cat)
        # Show first 300 chars
        print(result[:300] + ("..." if len(result) > 300 else ""))


def test_search():
    """Test Pinecone semantic search."""
    print("\n" + "=" * 60)
    print("TEST: Semantic Search (Pinecone)")
    print("=" * 60)

    queries = [
        "Tell me about your education and university",
        "What projects have you built?",
        "Why are you a good fit for this role?",
        "What experience do you have with voice AI?",
        "Tell me about the Dinner Talk project",
        "What are your weaknesses?",
        "What programming languages do you know?",
        "Tell me about your GitHub repos",
        "Do you have experience with LangGraph?",
        "What would you build at Scaler?",
    ]

    for query in queries:
        print(f"\n--- search_knowledge('{query}') ---")
        result = search_knowledge(query)
        # Show first 400 chars
        print(result[:400] + ("..." if len(result) > 400 else ""))


if __name__ == "__main__":
    test_lookup()
    test_search()
    print("\n\nLayer 1 tests complete!")
