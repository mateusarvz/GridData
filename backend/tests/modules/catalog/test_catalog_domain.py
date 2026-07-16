import pytest
from uuid import uuid4
from app.modules.catalog.domain.value_objects import ColumnType, Cardinality
from app.modules.catalog.domain.entities import (
    Workspace,
    Folder,
    TableDefinition,
    ColumnDefinition,
    Relationship
)
from app.shared.exceptions import DamaBoxDomainException

def test_workspace_folder_and_table_creation():
    owner_id = uuid4()
    ws = Workspace.create(name="Gestão Comercial", owner_id=owner_id)
    folder = Folder.create(name="Vendas", workspace_id=ws.id)
    table = TableDefinition.create(name="Leads", workspace_id=ws.id, folder_id=folder.id)
    
    assert table.workspace_id == ws.id
    assert table.folder_id == folder.id
    assert table.name == "Leads"
    assert len(table.columns) == 0

def test_add_column_to_table_with_limit_validation():
    table = TableDefinition.create(name="Clientes", workspace_id=uuid4())
    
    col_name = ColumnDefinition.create(
        table_id=table.id,
        name="Nome Completo",
        slug="nome_completo",
        col_type=ColumnType.TEXT,
        is_required=True
    )
    table.add_column(col_name)
    assert len(table.columns) == 1
    assert table.columns[0].col_type == ColumnType.TEXT
    
    # Testar limite máximo de 200 colunas por tabela
    for i in range(1, 200):
        table.add_column(ColumnDefinition.create(
            table_id=table.id,
            name=f"Col {i}",
            slug=f"col_{i}",
            col_type=ColumnType.TEXT
        ))
    
    assert len(table.columns) == 200
    
    with pytest.raises(DamaBoxDomainException, match="Limite máximo de 200 colunas"):
        table.add_column(ColumnDefinition.create(
            table_id=table.id,
            name="Col 201",
            slug="col_201",
            col_type=ColumnType.TEXT
        ))

def test_relationship_creation():
    rel = Relationship.create(
        name="Cliente Vendas",
        source_table_id=uuid4(),
        source_column_id=uuid4(),
        target_table_id=uuid4(),
        target_column_id=uuid4(),
        cardinality=Cardinality.ONE_TO_MANY
    )
    assert rel.cardinality == Cardinality.ONE_TO_MANY
