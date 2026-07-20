import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/gemini", tags=["Gemini Integration"])


class GeminiStatusResponse(BaseModel):
    connected: bool
    error: str | None = None


class GeminiChatRequest(BaseModel):
    prompt: str


class GeminiChatResponse(BaseModel):
    response: str
    error: str | None = None


def _gemini_url() -> str:
    return (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    )


async def _post_gemini(payload: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await client.post(_gemini_url(), json=payload)


@router.get("/status", response_model=GeminiStatusResponse)
async def get_gemini_status():
    if not settings.GEMINI_API_KEY:
        return GeminiStatusResponse(connected=False, error="GEMINI_API_KEY nao configurada.")

    # Status simples. Nao gasta quota.
    return GeminiStatusResponse(connected=True)


@router.post("/chat", response_model=GeminiChatResponse)
async def gemini_chat(dto: GeminiChatRequest):
    if not settings.GEMINI_API_KEY:
        return GeminiChatResponse(response="", error="GEMINI_API_KEY nao configurada.")

    try:
        payload = {
            "contents": [{"parts": [{"text": dto.prompt}]}],
            "systemInstruction": {
                "parts": [
                    {
                        "text": "Responda em portugues, curto, claro e direto. Sem introducao longa."
                    }
                ]
            },
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0.2},
        }

        response = await _post_gemini(payload)
        if response.status_code != 200:
            error_text = response.text
            if response.status_code == 429:
                return GeminiChatResponse(
                    response="",
                    error="HTTP 429: quota/billing/modelo bloqueando Gemini. Status nao prova conectividade.",
                )
            return GeminiChatResponse(response="", error=f"HTTP {response.status_code}: {error_text}")

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return GeminiChatResponse(response="", error="Sem resposta do Gemini.")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            return GeminiChatResponse(response="", error="Resposta vazia.")
        return GeminiChatResponse(response=text)
    except Exception as exc:
        return GeminiChatResponse(response="", error=str(exc))
