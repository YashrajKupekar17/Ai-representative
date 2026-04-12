"""
Main ingestion script. Run with:
    cd backend && python -m app.ingestion.ingest

Loads resume PDF + GitHub repos + persona.yaml → embeds → upserts to Pinecone.
Idempotent: safe to re-run (overwrites existing vectors by ID).
"""

import yaml
from pathlib import Path

from app.services.pinecone_client import upsert_chunks
from app.ingestion.resume_loader import load_resume
from app.ingestion.github_loader import load_github_repos


def load_persona_chunks() -> list[dict]:
    """Load persona.yaml as searchable chunks for nuanced questions."""
    persona_path = Path(__file__).parent.parent / "data" / "persona.yaml"
    with open(persona_path) as f:
        persona = yaml.safe_load(f)

    chunks = []

    # Why Scaler - important for "why are you right for this role?" questions
    why_points = persona.get("why_hire", [])
    if why_points:
        text = f"Why {persona['name']} is a great fit for Scaler:\n"
        text += "\n".join(f"- {point}" for point in why_points)
        chunks.append(
            {
                "id": "persona_why_hire",
                "text": text,
                "metadata": {"source": "personal", "section": "why_hire"},
            }
        )

    # Strengths
    strengths = persona.get("strengths", [])
    if strengths:
        text = f"{persona['name']}'s key strengths:\n"
        text += "\n".join(f"- {s}" for s in strengths)
        chunks.append(
            {
                "id": "persona_strengths",
                "text": text,
                "metadata": {"source": "personal", "section": "strengths"},
            }
        )

    # Weaknesses (for honest self-assessment questions)
    weaknesses = persona.get("weaknesses", [])
    if weaknesses:
        text = f"{persona['name']}'s areas for growth:\n"
        text += "\n".join(f"- {w}" for w in weaknesses)
        chunks.append(
            {
                "id": "persona_weaknesses",
                "text": text,
                "metadata": {"source": "personal", "section": "weaknesses"},
            }
        )

    print(f"  Loaded persona: {len(chunks)} chunks")
    return chunks


def main():
    all_chunks = []

    # 1. Resume
    resume_path = Path(__file__).parent.parent / "data" / "resume.pdf"
    if resume_path.exists():
        print("Loading resume...")
        all_chunks.extend(load_resume(resume_path))
    else:
        print(f"WARNING: No resume found at {resume_path}")
        print("  Place your resume.pdf in backend/app/data/resume.pdf")

    # 2. GitHub repos (skip if rate limited)
    print("\nLoading GitHub repos...")
    try:
        all_chunks.extend(load_github_repos())
    except Exception as e:
        print(f"  Skipping GitHub: {e}")
        print("  Repo info from persona.yaml will still be available via lookup_facts.")

    # 3. Persona facts (for semantic search on motivation/strengths)
    print("\nLoading persona facts...")
    all_chunks.extend(load_persona_chunks())

    # 4. Upsert to Pinecone
    if all_chunks:
        print(f"\nUpserting {len(all_chunks)} total chunks to Pinecone...")
        count = upsert_chunks(all_chunks)
        print(f"Done! {count} vectors upserted.")
    else:
        print("\nNo chunks to upsert. Check your data sources.")


if __name__ == "__main__":
    main()
