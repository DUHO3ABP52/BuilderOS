from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BuilderOS"
    app_env: str = "development"
    database_url: str = "sqlite:///./builderos.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
