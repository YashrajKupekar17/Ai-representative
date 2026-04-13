"""
Semantic cache for agent responses.
Embeds user queries and checks cosine similarity against cached entries.
Cache hit avoids the full GPT-4o + tool-call pipeline.

Only caches knowledge queries (not calendar — those are time-sensitive).
"""

import time
import numpy as np
import structlog

from app.services.embeddings import embed_text

logger = structlog.get_logger()

# In-memory cache: list of {embedding, query, response, sources, timestamp}
_cache: list[dict] = []

# Tuning knobs
SIMILARITY_THRESHOLD = 0.92  # cosine similarity to count as a hit
MAX_CACHE_SIZE = 200
CACHE_TTL_SECONDS = 3600  # 1 hour


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def _is_calendar_query(query: str) -> bool:
    """Calendar queries should never be cached (time-sensitive)."""
    calendar_keywords = [
        "schedule", "book", "meeting", "slot", "available", "calendar",
        "appointment", "call me", "set up a call",
    ]
    q_lower = query.lower()
    return any(kw in q_lower for kw in calendar_keywords)


def _evict_stale():
    """Remove expired entries."""
    global _cache
    now = time.time()
    _cache = [e for e in _cache if now - e["timestamp"] < CACHE_TTL_SECONDS]


def cache_lookup(query: str) -> dict | None:
    """
    Check if a semantically similar query exists in cache.
    Returns {"response": str, "sources": list} on hit, None on miss.
    """
    if _is_calendar_query(query):
        logger.info("cache_skip", reason="calendar_query", query=query[:80])
        return None

    _evict_stale()

    if not _cache:
        logger.info("cache_miss", reason="empty_cache", query=query[:80])
        return None

    start = time.time()
    query_embedding = embed_text(query)
    embed_ms = round((time.time() - start) * 1000)

    best_sim = 0.0
    best_entry = None

    for entry in _cache:
        sim = _cosine_similarity(query_embedding, entry["embedding"])
        if sim > best_sim:
            best_sim = sim
            best_entry = entry

    if best_sim >= SIMILARITY_THRESHOLD and best_entry is not None:
        logger.info(
            "cache_hit",
            query=query[:80],
            cached_query=best_entry["query"][:80],
            similarity=round(best_sim, 4),
            embed_ms=embed_ms,
        )
        return {
            "response": best_entry["response"],
            "sources": best_entry["sources"],
            "cache_hit": True,
        }

    logger.info(
        "cache_miss",
        query=query[:80],
        best_similarity=round(best_sim, 4),
        embed_ms=embed_ms,
    )
    return None


def cache_store(query: str, response: str, sources: list):
    """Store a query-response pair in the cache."""
    if _is_calendar_query(query):
        return

    _evict_stale()

    # Don't cache error responses
    if "trouble processing" in response.lower():
        return

    start = time.time()
    embedding = embed_text(query)
    embed_ms = round((time.time() - start) * 1000)

    # Check if a very similar entry already exists (avoid near-duplicates)
    for entry in _cache:
        if _cosine_similarity(embedding, entry["embedding"]) >= 0.98:
            logger.debug("cache_store_skip", reason="near_duplicate", query=query[:80])
            return

    _cache.append({
        "embedding": embedding,
        "query": query,
        "response": response,
        "sources": sources,
        "timestamp": time.time(),
    })

    # Evict oldest if over capacity
    if len(_cache) > MAX_CACHE_SIZE:
        _cache.pop(0)

    logger.info(
        "cache_store",
        query=query[:80],
        cache_size=len(_cache),
        embed_ms=embed_ms,
    )


def cache_stats() -> dict:
    """Return cache statistics."""
    _evict_stale()
    return {
        "size": len(_cache),
        "max_size": MAX_CACHE_SIZE,
        "ttl_seconds": CACHE_TTL_SECONDS,
        "similarity_threshold": SIMILARITY_THRESHOLD,
    }
