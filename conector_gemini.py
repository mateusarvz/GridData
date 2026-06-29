import os
from dotenv import load_dotenv
import google.generativeai as genai

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configura API key do Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY não encontrada em .env")

genai.configure(api_key=api_key)

# Inicializa modelo
model = genai.GenerativeModel("gemini-2.0-flash")

def chat_with_gemini(prompt: str) -> str:
    """Envia prompt ao Gemini e retorna resposta."""
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    # Exemplo de uso
    test_prompt = "Olá, como você está?"
    response = chat_with_gemini(test_prompt)
    print(f"Prompt: {test_prompt}")
    print(f"Resposta: {response}")
