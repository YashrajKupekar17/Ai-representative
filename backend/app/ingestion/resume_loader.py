"""
Load resume PDF and split into section-aware chunks.
Splits by detected section headers (Education, Experience, Skills, etc.)
then chunks each section with token-based splitting.
"""

import re
from pathlib import Path

import tiktoken
from PyPDF2 import PdfReader

# Section header patterns commonly found in resumes
SECTION_HEADERS = [
    "education",
    "experience",
    "work experience",
    "projects",
    "skills",
    "technical skills",
    "certifications",
    "achievements",
    "summary",
    "objective",
    "publications",
    "awards",
    "interests",
    "extracurricular",
]

enc = tiktoken.encoding_for_model("gpt-4o")


def _count_tokens(text: str) -> int:
    return len(enc.encode(text))


def _chunk_text(text: str, max_tokens: int = 400, overlap_tokens: int = 50) -> list[str]:
    """Split text into chunks by token count with overlap."""
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text.strip())
        start = end - overlap_tokens
    return [c for c in chunks if c]  # filter empty


def _detect_section(line: str) -> str | None:
    """Check if a line is a section header. Returns section name or None."""
    clean = line.strip().lower().rstrip(":")
    for header in SECTION_HEADERS:
        if clean == header or clean.startswith(header):
            return header.replace(" ", "_")
    return None


def load_resume(pdf_path: str | Path) -> list[dict]:
    """
    Load resume PDF and return chunks with metadata.
    Returns: [{"id": str, "text": str, "metadata": {"source": "resume", "section": str}}]
    """
    reader = PdfReader(str(pdf_path))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    # Split into sections
    lines = full_text.split("\n")
    sections: list[tuple[str, list[str]]] = []
    current_section = "general"
    current_lines: list[str] = []

    for line in lines:
        detected = _detect_section(line)
        if detected:
            if current_lines:
                sections.append((current_section, current_lines))
            current_section = detected
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_section, current_lines))

    # Chunk each section
    chunks = []
    for section_name, section_lines in sections:
        section_text = "\n".join(section_lines).strip()
        if not section_text:
            continue

        if _count_tokens(section_text) <= 400:
            # Small enough to be one chunk
            chunks.append(
                {
                    "id": f"resume_{section_name}_0",
                    "text": section_text,
                    "metadata": {"source": "resume", "section": section_name},
                }
            )
        else:
            for i, chunk_text in enumerate(_chunk_text(section_text)):
                chunks.append(
                    {
                        "id": f"resume_{section_name}_{i}",
                        "text": chunk_text,
                        "metadata": {"source": "resume", "section": section_name},
                    }
                )

    print(f"  Loaded resume: {len(chunks)} chunks from {len(sections)} sections")
    return chunks
