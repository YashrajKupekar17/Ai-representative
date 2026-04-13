from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "ai-persona"
    calcom_api_key: str = ""
    calcom_event_type_id: int = 0
    calcom_api_version: str = "2024-06-14"
    calcom_username: str = "yashraj-ml-sxvdwl"
    github_username: str = "YashrajKupekar17"

    # Embedding model
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1024

    # LLM
    llm_model: str = "gpt-4o"

    # Vapi
    vapi_api_key: str = ""

    # Base URL for the API (used for resume download link etc.)
    api_base_url: str = "http://localhost:8000"

    # Frontend URL for CORS (comma-separated for multiple origins)
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
