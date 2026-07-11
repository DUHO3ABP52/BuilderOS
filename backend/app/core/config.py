from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BuilderOS"
    app_env: str = "development"
    database_url: str = "sqlite:///./builderos.db"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    first_user_email: str = "admin@example.com"
    first_user_password: str = "change-me"
    first_user_name: str = "Администратор"

    redis_url: str = "redis://localhost:6379/0"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "builderos"
    minio_secret_key: str = "builderos-secret"
    minio_bucket: str = "builderos"
    minio_secure: bool = False

    # Локальная LLM (Ollama) + опциональный OmniRoute / OpenAI-compatible
    llm_enabled: bool = True
    llm_provider: str = "hybrid"  # ollama | omniroute | hybrid
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 60.0
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_auto_pull: bool = True
    # Fallback / OmniRoute (бесплатные провайдеры через локальный gateway)
    llm_fallback_base_url: str = "http://localhost:20128"
    llm_fallback_model: str = "auto/cheap"
    llm_fallback_api_key: str = ""
    # Фрагменты базы знаний уходят в облако только при явном разрешении
    llm_cloud_for_knowledge: bool = False

    # RAG / Qdrant
    rag_enabled: bool = True
    rag_collection: str = "builderos_knowledge"
    rag_top_k: int = 8
    rag_score_threshold: float = 0.15
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768
    embedding_base_url: str = ""  # пусто = llm_base_url / Ollama
    embedding_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
