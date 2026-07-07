import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_rfc_7807_validation_error_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Tentar chamar endpoint que não existe ou forçar erro de validação (ex: rota de teste)
        response = await client.get("/api/v1/test-error")
        assert response.status_code == 400
        
        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert data["status"] == 400
