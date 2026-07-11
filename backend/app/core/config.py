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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
