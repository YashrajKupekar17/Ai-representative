"""
Hybrid knowledge service: structured YAML lookup + Pinecone vector search.

- lookup_facts(): deterministic, fast, for factual questions
- search_knowledge(): semantic, for nuanced/detailed questions
- GPT-4o function calling decides which to use
"""

import yaml
from pathlib import Path

from app.services.pinecone_client import search

# Load persona YAML once at import time
_persona_path = Path(__file__).parent.parent / "data" / "persona.yaml"
with open(_persona_path) as f:
    PERSONA = yaml.safe_load(f)


def lookup_facts(category: str) -> str:
    """
    Look up structured facts from persona.yaml.
    Categories: education, experience, skills, github_repos, why_scaler,
                strengths, weaknesses, availability, all
    """
    if category == "all":
        return yaml.dump(PERSONA, default_flow_style=False)

    value = PERSONA.get(category)
    if value is None:
        return f"No structured data found for category: {category}"

    if isinstance(value, (dict, list)):
        return yaml.dump(value, default_flow_style=False)
    return str(value)


def search_knowledge(query: str, source_filter: str | None = None) -> str:
    """
    Semantic search over Pinecone for detailed/nuanced questions.
    source_filter: optional, one of "resume", "github", "personal"
    Returns formatted context string with sources.
    """
    filter_dict = None
    if source_filter:
        filter_dict = {"source": source_filter}

    results = search(query, top_k=5, filter=filter_dict)

    if not results:
        return "No relevant information found in the knowledge base."

    # Format results with source attribution
    context_parts = []
    for i, r in enumerate(results, 1):
        source = r["metadata"].get("source", "unknown")
        section = r["metadata"].get("section", "")
        repo = r["metadata"].get("repo_name", "")

        label = f"[{source}"
        if repo:
            label += f"/{repo}"
        if section:
            label += f"/{section}"
        label += f" | relevance: {r['score']:.2f}]"

        context_parts.append(f"{label}\n{r['text']}")

    return "\n\n---\n\n".join(context_parts)
