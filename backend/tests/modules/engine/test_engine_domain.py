import pytest
from uuid import uuid4
from app.modules.engine.domain.value_objects import RowData, FilterOperator
from app.modules.engine.domain.entities import DynamicRow
from app.shared.exceptions import DamaBoxDomainException

def test_row_data_value_object():
    rd = RowData({"nome": "Davi", "idade": 30, "ativo": True})
    assert rd.value["nome"] == "Davi"
    assert rd.value["idade"] == 30
    
    # Testar que não aceita valores não serializáveis em JSON
    class NãoSerializavel:
        pass
    
    with pytest.raises(DamaBoxDomainException, match="não é serializável"):
        RowData({"invalido": NãoSerializavel()})

def test_dynamic_row_creation_and_version_bump():
    table_id = uuid4()
    row = DynamicRow.create(table_id=table_id, data={"cliente": "Dama Box", "valor": 1500.50})
    
    assert row.table_id == table_id
    assert row.data["cliente"] == "Dama Box"
    assert row.version == 1
    
    # Atualizar dados e incrementar versão
    row.update_data({"cliente": "Dama Box Corp", "valor": 2000.00})
    assert row.data["cliente"] == "Dama Box Corp"
    assert row.version == 2

def test_filter_operator():
    assert FilterOperator.EQ == "eq"
    assert FilterOperator.LIKE == "like"
    assert FilterOperator.CONTAINS == "contains"
