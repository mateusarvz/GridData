from datetime import date, timedelta
from typing import Any

from app.core.config import settings

try:
    from supabase import Client, create_client
    from supabase_auth.errors import AuthApiError
except ImportError:  # pragma: no cover
    Client = Any  # type: ignore
    create_client = None  # type: ignore
    AuthApiError = Exception  # type: ignore

FREE_PLAN_ID = "19b51ec9-bda7-4d93-8933-6ee11cd1ae30"


def get_free_plan_id(client: Client) -> str | None:
    try:
        response = (
            client
            .from_('subscription_plans')
            .select('id')
            .eq('id', FREE_PLAN_ID)
            .maybe_single()
            .execute()
        )
        plan = getattr(response, 'data', None)
        if plan and isinstance(plan, dict):
            return plan.get('id')

        response = (
            client
            .from_('subscription_plans')
            .select('id')
            .eq('nome', 'Free')
            .maybe_single()
            .execute()
        )
        plan = getattr(response, 'data', None)
        if plan and isinstance(plan, dict):
            return plan.get('id')

        return None
    except Exception:
        return None


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


def authenticate_user_main(email: str, senha: str) -> dict[str, Any]:
    auth_client = get_supabase_client()
    service_client = get_supabase_service_client()

    if auth_client is None:
        return {
            "ok": False,
            "error": "Cliente Supabase (anon) não configurado corretamente.",
        }

    try:
        auth_response = auth_client.auth.sign_in_with_password({
            "email": email,
            "password": senha,
        })

        user = getattr(auth_response, 'user', None)

        if user is None:
            return {"ok": False, "error": "Usuário não encontrado ou credenciais inválidas."}

        user_email = getattr(user, 'email', None)
        user_id = getattr(user, 'id', None)

        if not user_email or not user_id:
            return {"ok": False, "error": "Dados do usuário Supabase inválidos."}

        lookup_client = service_client or auth_client
        response = (
            lookup_client
            .from_('users')
            .select('id, nome_usuario, email')
            .eq('email', user_email)
            .maybe_single()
            .execute()
        )

        data = getattr(response, 'data', None)
        if data:
            return {
                "ok": True,
                "user": {
                    "user_exists": True,
                    "id": data.get('id'),
                    "nome_usuario": data.get('nome_usuario'),
                    "email": data.get('email'),
                }
            }

        return {
            "ok": True,
            "user": {
                "user_exists": False,
                "email": user_email,
            }
        }
    except AuthApiError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}


def create_profile_for_supabase_user(email: str, nome_usuario: str) -> dict[str, Any]:
    client = get_supabase_service_client()
    if client is None:
        return {
            "ok": False,
            "error": "Chave service_role do Supabase não está configurada no backend.",
        }

    try:
        response = (
            client
            .from_('users')
            .select('id')
            .eq('email', email)
            .maybe_single()
            .execute()
        )
        existing = getattr(response, 'data', None)
        if existing:
            return {"ok": False, "error": "Já existe um perfil com este email."}

        insert_response = (
            client
            .from_('users')
            .insert([
                {
                    "email": email,
                    "nome_usuario": nome_usuario,
                }
            ])
            .select('id, nome_usuario, email')
            .execute()
        )
        user_data = getattr(insert_response, 'data', None)
        if isinstance(user_data, list):
            user_data = user_data[0] if user_data else None

        if not user_data:
            return {"ok": False, "error": "Falha ao criar usuário."}

        plan_id = get_free_plan_id(client)
        if plan_id is None:
            return {"ok": False, "error": "Plano Free não encontrado no Supabase."}

        subscription_response = (
            client
            .from_('user_subscriptions')
            .insert([
                {
                    "user_id": user_data.get('id'),
                    "plan_id": plan_id,
                    "data_vencimento": (date.today() + timedelta(days=30)).isoformat(),
                }
            ])
            .execute()
        )
        subscription_data = getattr(subscription_response, 'data', None)
        if isinstance(subscription_data, list):
            subscription_data = subscription_data[0] if subscription_data else None

        if not subscription_data:
            return {"ok": False, "error": "Falha ao criar assinatura do usuário."}

        return {
            "ok": True,
            "user_id": user_data.get('id'),
            "nome_usuario": user_data.get('nome_usuario'),
            "email": user_data.get('email'),
        }
    except AuthApiError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}


def get_subscription_plans() -> dict[str, Any]:
    service_client = get_supabase_service_client()
    if service_client is None:
        return {"ok": False, "error": "Supabase service role key não configurada.", "plans": []}

    try:
        response = (
            service_client
            .from_('subscription_plans')
            .select('id, nome, descricao, preco_mensal')
            .order('nome', ascending=True)
            .execute()
        )
        plans = getattr(response, 'data', []) or []
        return {"ok": True, "plans": plans}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc), "plans": []}
