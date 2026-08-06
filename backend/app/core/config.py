from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    candidates: list[Path] = []
    current_dir = Path.cwd().resolve()
    backend_dir = Path(__file__).resolve().parents[2]
    project_root = backend_dir.parent

    for base in (current_dir, backend_dir, project_root):
        candidates.append(base / ".env")
        candidates.append(base / "backend" / ".env")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


ENV_FILE = find_env_file()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dama Box"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Banco Administrativo
    DATABASE_SYSTEM_URL: str = "postgresql+asyncpg://damabox_admin:change-me@localhost:5432/sistema"

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production-for-security-purposes-and-keep-it-secret"
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
    GEMINI_API_KEY2: str = ""
    GEMINI_API_KEY3: str = ""
    GEMINI_API_KEY4: str = ""
    GEMINI_API_KEY5: str = ""
    GEMINI_API_NAME: str = "DamaBox API Key"
    GEMINI_PROJECT_NAME: str = ""
    GEMINI_PROJECT_NUMBER: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    @property
    def GEMINI_API_KEYS(self) -> list[str]:
        return [
            key.strip()
            for key in (
                self.GEMINI_API_KEY,
                self.GEMINI_API_KEY2,
                self.GEMINI_API_KEY3,
                self.GEMINI_API_KEY4,
                self.GEMINI_API_KEY5,
            )
            if key and key.strip()
        ]

    @property
    def GEMINI_API_KEY_EFFECTIVE(self) -> str:
        return self.GEMINI_API_KEYS[0] if self.GEMINI_API_KEYS else ""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")


settings = Settings()
