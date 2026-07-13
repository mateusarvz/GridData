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
    SUPABASE_URL: str = "https://gleprxpuiddllodlhizm.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdsZXByeHB1aWRkbGxvZGxoaXptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM5NDc5NzQsImV4cCI6MjA5OTUyMzk3NH0.UQchb58g84tsuOPqjmRuRTLEKoNYH0ZiNQjWQf_Uedw"
    SUPABASE_SERVICE_ROLE_KEY: str = "sb_secret_Nfcy9VBzo21KhclcICqm8g_F84U467U"
    JWT_SECRET_SUPABASE: str = "umT0zWR+48szS+jkEcZM+TRcrV39kYg5ztW31nsvSHbHQcmriizL4krKCAuu7AeOSitayvwsCtkzC6QaOcYuJA=="

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
