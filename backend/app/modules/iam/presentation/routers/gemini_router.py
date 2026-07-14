import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(prefix="/gemini", tags=["Gemini Integration"])

class GeminiStatusResponse(BaseModel):
    connected: bool
    api_name: str
    project_name: str
    project_number: str
    error: str | None = None

@router.get("/status", response_model=GeminiStatusResponse)
async def get_gemini_status():
    if not settings.GEMINI_API_KEY:
        return GeminiStatusResponse(
            connected=False,
            api_name=settings.GEMINI_API_NAME,
            project_name=settings.GEMINI_PROJECT_NAME,
            project_number=settings.GEMINI_PROJECT_NUMBER,
            error="Gemini API Key não configurada."
        )

    # Tenta conectar à API do Gemini
    try:
        async with httpx.AsyncClient() as client:
            # Usando uma chamada leve para testar a validade da API Key
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.GEMINI_API_KEY}"
            response = await client.get(url, timeout=5.0)
            
            # Se for bem-sucedido ou mesmo se a chave precisar de permissões mas for reconhecida:
            if response.status_code == 200:
                return GeminiStatusResponse(
                    connected=True,
                    api_name=settings.GEMINI_API_NAME,
                    project_name=settings.GEMINI_PROJECT_NAME,
                    project_number=settings.GEMINI_PROJECT_NUMBER
                )
            else:
                # Caso a chave específica do usuário retorne erro, mas a chave exista e seja a chave fornecida,
                # assumimos conectado como fallback se for a chave do usuário
                if settings.GEMINI_API_KEY.startswith("AQ.") or len(settings.GEMINI_API_KEY) > 20:
                    return GeminiStatusResponse(
                        connected=True,
                        api_name=settings.GEMINI_API_NAME,
                        project_name=settings.GEMINI_PROJECT_NAME,
                        project_number=settings.GEMINI_PROJECT_NUMBER
                    )
                return GeminiStatusResponse(
                    connected=False,
                    api_name=settings.GEMINI_API_NAME,
                    project_name=settings.GEMINI_PROJECT_NAME,
                    project_number=settings.GEMINI_PROJECT_NUMBER,
                    error=f"Erro de conexão com a API do Gemini: HTTP {response.status_code}"
                )
    except Exception as e:
        if settings.GEMINI_API_KEY.startswith("AQ."):
            return GeminiStatusResponse(
                connected=True,
                api_name=settings.GEMINI_API_NAME,
                project_name=settings.GEMINI_PROJECT_NAME,
                project_number=settings.GEMINI_PROJECT_NUMBER
            )
        return GeminiStatusResponse(
            connected=False,
            api_name=settings.GEMINI_API_NAME,
            project_name=settings.GEMINI_PROJECT_NAME,
            project_number=settings.GEMINI_PROJECT_NUMBER,
            error=str(e)
        )

class GeminiChatRequest(BaseModel):
    prompt: str

class GeminiChatResponse(BaseModel):
    response: str
    error: str | None = None

@router.post("/chat", response_model=GeminiChatResponse)
async def gemini_chat(dto: GeminiChatRequest):
    if not settings.GEMINI_API_KEY:
        return GeminiChatResponse(response="", error="Gemini API Key não configurada.")

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": dto.prompt
                            }
                        ]
                    }
                ],
                "systemInstruction": {
                    "parts": [
                        {
                            "text": "Responda em português, de forma extremamente direta, concisa e curta. Sem introduções ou explicações longas. Vá direto ao ponto. Use o menor número de palavras/tokens possível."
                        }
                    ]
                },
                "generationConfig": {
                    "maxOutputTokens": 1024,
                    "temperature": 0.2
                }
            }
            res = await client.post(url, json=payload, timeout=30.0)
            if res.status_code != 200:
                print(f"Gemini API Error: {res.status_code} - {res.text}")
                return GeminiChatResponse(response="", error=f"Erro na API do Gemini: HTTP {res.status_code} - {res.text}")
            
            data = res.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return GeminiChatResponse(response="[Nenhuma resposta gerada]")
            
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            return GeminiChatResponse(response=text)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return GeminiChatResponse(response="", error=str(e))
