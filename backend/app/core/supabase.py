from typing import Any

from app.core.config import settings

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover
    Client = Any  # type: ignore
    create_client = None  # type: ignore


def get_supabase_client() -> Client | None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None
    if create_client is None:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase_service_client() -> Client | None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    if create_client is None:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_status() -> dict[str, Any]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return {
            "ok": False,
            "error": "Variáveis de ambiente do Supabase ausentes.",
        }

    try:
        client = get_supabase_client()
        if client is None:
            return {
                "ok": False,
                "error": "Cliente Supabase não pôde ser criado.",
            }
        return {
            "ok": True,
            "message": "Cliente Supabase configurado.",
            "url": settings.SUPABASE_URL,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "error": str(exc),
        }


def authenticate_user_main(nome_usuario: str, email: str, senha: str) -> dict[str, Any]:
    service_client = get_supabase_service_client()
    if service_client is None:
        return {
            "ok": False,
            "error": "Supabase service role key não configurada.",
        }

    try:
        response = (
            service_client
            .from_('user_main')
            .select('id, nome_usuario, email, user_id')
            .eq('nome_usuario', nome_usuario)
            .eq('email', email)
            .eq('senha', senha)
            .maybe_single()
            .execute()
        )

        if response is None:
            return {"ok": False, "error": "Usuario não encontrado."}

        data = getattr(response, 'data', None)
        if not data:
            return {"ok": False, "error": "Usuario não encontrado."}

        return {"ok": True, "user": data}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}
