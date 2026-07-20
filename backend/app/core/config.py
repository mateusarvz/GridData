from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dama Box"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Banco Administrativo
    DATABASE_SYSTEM_URL: str = "postgresql+asyncpg://damabox_admin:change-me@localhost:5432/sistema"

    # Auth
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Redis & Storage
    REDIS_URL: str = "redis://localhost:6379/0"
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "change-me"
    MINIO_SECRET_KEY: str = "change-me"
    MINIO_BUCKET_NAME: str = "damabox-storage"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    JWT_SECRET_SUPABASE: str = ""

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_API_NAME: str = "DamaBox API Key"
    GEMINI_PROJECT_NAME: str = ""
    GEMINI_PROJECT_NUMBER: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
