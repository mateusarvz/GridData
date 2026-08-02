import importlib
import sys
from pathlib import Path


def test_settings_loads_backend_env_file_when_started_from_repo_root(tmp_path, monkeypatch):
    project_root = tmp_path / "repo"
    backend_dir = project_root / "backend"
    backend_dir.mkdir(parents=True)
    (backend_dir / ".env").write_text(
        "PROJECT_NAME=Loaded from backend env\n"
        "SUPABASE_URL=https://example.supabase.co\n"
        "SUPABASE_ANON_KEY=anon-key\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project_root)
    monkeypatch.syspath_prepend(str(backend_dir))
    sys.modules.pop("app.core.config", None)

    config_module = importlib.import_module("app.core.config")
    settings = config_module.Settings()

    assert settings.PROJECT_NAME == "Loaded from backend env"
    assert settings.SUPABASE_URL == "https://example.supabase.co"
    assert settings.SUPABASE_ANON_KEY == "anon-key"
