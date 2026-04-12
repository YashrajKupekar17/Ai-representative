from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "ai-persona"
    calcom_api_key: str = ""
    calcom_event_type_id: int = 0
    github_username: str = "YashrajKupekar17"

    # Embedding model
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1024

    # LLM
    llm_model: str = "gpt-4o"

    class Config:
        env_file = ".env"


settings = Settings()
