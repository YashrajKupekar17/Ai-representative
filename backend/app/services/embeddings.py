from openai import OpenAI

from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    response = client.embeddings.create(
        input=text,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    return response.data[0].embedding


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts."""
    response = client.embeddings.create(
        input=texts,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    return [item.embedding for item in response.data]
