from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.supabase import authenticate_user_main

router = APIRouter(prefix="", tags=["Supabase Auth"])

class SupabaseLoginRequest(BaseModel):
    nome_usuario: str
    email: str
    senha: str

class SupabaseLoginResponse(BaseModel):
    ok: bool
    user_id: str | None = None
    nome_usuario: str | None = None
    email: str | None = None
    error: str | None = None

@router.post("/login", response_model=SupabaseLoginResponse)
async def supabase_login(dto: SupabaseLoginRequest):
    result = authenticate_user_main(dto.nome_usuario, dto.email, dto.senha)
    if not result["ok"]:
        return {
            "ok": False,
            "error": result["error"],
            "user_id": None,
            "nome_usuario": None,
            "email": None,
        }

    return {
        "ok": True,
        "user_id": result["user"]["user_id"],
        "nome_usuario": result["user"]["nome_usuario"],
        "email": result["user"]["email"],
        "error": None,
    }
