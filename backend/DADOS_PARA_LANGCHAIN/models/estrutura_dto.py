"""
Pydantic DTOs for the LangChain-accessible structure endpoint.

These models contain ONLY structural metadata — no row data ever.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ColunaSchema(BaseModel):
    """Single column definition extracted from information_schema.columns."""

    nome: str = Field(description="Column name")
    tipo: str = Field(description="PostgreSQL data type (e.g. bigint, text, timestamp)")
    nullable: bool = Field(description="Whether the column accepts NULL values")


class RelacionamentoInfo(BaseModel):
    """Foreign-key relationship between a user table and the master users_table catalog."""

    coluna_local: str = Field(description="Column in the user table that holds the FK (e.g. users_table_id)")
    referencia: str = Field(description="Full reference in schema.table.column form (e.g. table_schema.users_table.id)")


class TabelaSchema(BaseModel):
    """One table visible to the LangChain SQL Agent — metadata + columns + FK relationship."""

    nome_tabela: str = Field(description="Physical table name in the table_schema schema")
    origem_arquivo: str | None = Field(None, description="Original uploaded file name")
    tipo_arquivo: str | None = Field(None, description="Original file type (csv, xlsx, etc.)")
    total_linhas: int = Field(0, description="Row count recorded at upload time")
    criado_em: datetime | None = Field(None, description="When the table was first created")
    colunas: list[ColunaSchema] = Field(default_factory=list, description="Column definitions")
    relacionamento: RelacionamentoInfo | None = Field(None, description="FK link to users_table")


class EstruturaAcessivelResponse(BaseModel):
    """
    Top-level response for GET /agente-ia/estrutura-acessivel.

    Contains ONLY schema structure — never row data. See buildAgentSchemaContext
    for the text/DDL variant meant to be injected into the SQL Agent prompt.
    """

    tabelas: list[TabelaSchema] = Field(default_factory=list)
