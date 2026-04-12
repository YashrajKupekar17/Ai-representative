from pinecone import Pinecone

from app.config import settings
from app.services.embeddings import embed_text

pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)


def upsert_chunks(chunks: list[dict]) -> int:
    """
    Upsert chunks to Pinecone.
    Each chunk: {"id": str, "text": str, "metadata": dict}
    """
    # Embed all texts
    texts = [c["text"] for c in chunks]
    # Batch embed (max 2048 per API call)
    from app.services.embeddings import embed_texts

    vectors = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_embeddings = embed_texts(batch_texts)
        for j, emb in enumerate(batch_embeddings):
            chunk = chunks[i + j]
            vectors.append(
                {
                    "id": chunk["id"],
                    "values": emb,
                    "metadata": {**chunk["metadata"], "text": chunk["text"]},
                }
            )

    # Upsert in batches of 100
    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i : i + 100])

    return len(vectors)


def search(query: str, top_k: int = 5, filter: dict | None = None) -> list[dict]:
    """
    Search Pinecone for relevant chunks.
    Returns list of {"text": str, "score": float, "metadata": dict}
    """
    query_embedding = embed_text(query)

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter,
    )

    return [
        {
            "text": match["metadata"].get("text", ""),
            "score": match["score"],
            "metadata": {
                k: v for k, v in match["metadata"].items() if k != "text"
            },
        }
        for match in results["matches"]
    ]
