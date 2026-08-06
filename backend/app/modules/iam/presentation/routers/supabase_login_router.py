from fastapi import APIRouter
from pydantic import BaseModel
from app.core.supabase import (
    authenticate_user_main,
    create_profile_for_supabase_user,
    handle_google_oauth,
)

router = APIRouter(prefix="", tags=["Supabase Auth"])

class SupabaseLoginRequest(BaseModel):
    email: str
    senha: str

class SupabaseLoginResponse(BaseModel):
    ok: bool
    user_exists: bool = False
    user_id: str | None = None
    nome_usuario: str | None = None
    email: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    error: str | None = None

class GoogleOAuthCallbackRequest(BaseModel):
    access_token: str

class CreateProfileRequest(BaseModel):
    email: str
    nome_usuario: str
    auth_user_id: str | None = None

class CreateProfileResponse(BaseModel):
    ok: bool
    user_id: str | None = None
    nome_usuario: str | None = None
    email: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    error: str | None = None

@router.post("/login", response_model=SupabaseLoginResponse)
async def supabase_login(dto: SupabaseLoginRequest):
    result = authenticate_user_main(dto.email, dto.senha)
    if not result["ok"]:
        return {
            "ok": False,
            "error": result["error"],
            "user_exists": False,
            "user_id": None,
            "nome_usuario": None,
            "email": None,
            "access_token": None,
            "refresh_token": None,
        }

    user = result["user"]
    return {
        "ok": True,
        "user_exists": user.get("user_exists", False),
        "user_id": user.get("id"),
        "nome_usuario": user.get("nome_usuario"),
        "email": user.get("email"),
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "error": None,
    }

@router.post("/google/callback", response_model=SupabaseLoginResponse)
async def google_oauth_callback(dto: GoogleOAuthCallbackRequest):
    result = handle_google_oauth(dto.access_token)
    if not result["ok"]:
        return {
            "ok": False,
            "error": result["error"],
            "user_exists": False,
            "user_id": None,
            "nome_usuario": None,
            "email": None,
            "access_token": None,
            "refresh_token": None,
        }

    user = result["user"]
    return {
        "ok": True,
        "user_exists": user.get("user_exists", False),
        "user_id": user.get("id"),
        "nome_usuario": user.get("nome_usuario"),
        "email": user.get("email"),
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "error": None,
    }

@router.post("/create-profile", response_model=CreateProfileResponse)
async def create_profile(dto: CreateProfileRequest):
    result = create_profile_for_supabase_user(
        dto.email,
        dto.nome_usuario,
        dto.auth_user_id,
    )

    if not result["ok"]:
        return {
            "ok": False,
            "error": result["error"],
            "user_id": None,
            "nome_usuario": None,
            "email": None,
            "access_token": None,
            "refresh_token": None,
        }

    return {
        "ok": True,
        "user_id": result["user_id"],
        "nome_usuario": result["nome_usuario"],
        "email": result["email"],
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "error": None,
    }
