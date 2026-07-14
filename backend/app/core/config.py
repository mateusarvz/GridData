from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dama Box"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Banco Administrativo
    DATABASE_SYSTEM_URL: str = "postgresql+asyncpg://damabox_admin:damabox_password_secret@localhost:5432/sistema"

    # Auth
    JWT_SECRET_KEY: str = "b914d7a8c3d2e1f0a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Redis & Storage
    REDIS_URL: str = "redis://localhost:6379/0"
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "damabox_minio_admin"
    MINIO_SECRET_KEY: str = "damabox_minio_secret"
    MINIO_BUCKET_NAME: str = "damabox-storage"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    JWT_SECRET_SUPABASE: str = ""

    # Gemini
    GEMINI_API_KEY: str = "AQ.Ab8RN6LxQOXFoMlmafduXFVjSLrhDYqvecQvWrS48BZYPhrklg"
    GEMINI_API_NAME: str = "DamaBox API Key"
    GEMINI_PROJECT_NAME: str = "projects/915600202325"
    GEMINI_PROJECT_NUMBER: str = "915600202325"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
