import pytest
from app.core.database import db_manager

@pytest.mark.asyncio
async def test_tenant_engine_caching():
    tenant_name_1 = "empresa_0001"
    
    # Primeira requisição cria e armazena no cache
    engine_1 = db_manager.get_tenant_engine(tenant_name_1)
    assert engine_1 is not None
    assert tenant_name_1 in db_manager._tenant_engines
    
    # Segunda requisição deve retornar exatamente a mesma engine em cache (mesmo ID em memória)
    engine_2 = db_manager.get_tenant_engine(tenant_name_1)
    assert id(engine_1) == id(engine_2)
    
    # Engine de outra empresa deve ser diferente
    engine_other = db_manager.get_tenant_engine("empresa_0002")
    assert id(engine_1) != id(engine_other)
    assert "empresa_0002" in db_manager._tenant_engines
