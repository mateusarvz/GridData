# Arquitetura da Plataforma de Organização de Dados

## Visão Geral

O projeto deve ser tratado como uma plataforma de **Data Management +
Semantic Layer**, e não apenas um organizador de planilhas.

Objetivos: - Organizar dados empresariais (vendas, estoque, financeiro
etc.). - Permitir importação de arquivos e relacionamento entre
tabelas. - Servir de base para análises e futuras aplicações com LLMs.

## Arquitetura Geral

``` text
                Frontend
                    │
                    ▼
            API Backend (FastAPI)
                    │
        ┌───────────┼──────────────┐
        │           │              │
        ▼           ▼              ▼
 Metadata DB   Data Engine    File Storage
 PostgreSQL    SQLAlchemy      Local Storage

                    │
                    ▼
             Business Layer

                    │
                    ▼
         AI / Analytics Layer (futuro)
```

## Stack Tecnológica

### Backend

-   Python
-   FastAPI
-   SQLAlchemy 2.0
-   Alembic
-   Pydantic v2

### Banco de Dados

-   PostgreSQL
-   Docker + Docker Compose
-   DBeaver

### Frontend

-   React
-   TypeScript
-   Vite
-   TailwindCSS
-   Shadcn UI
-   TanStack Table
-   TanStack Query
-   Zustand

### Importação de Dados

-   Pandas
-   Polars
-   OpenPyXL
-   PyArrow

## Organização do Backend

``` text
backend/
  app/
    api/
    services/
    repositories/
    models/
    schemas/
    database/
    core/
    utils/
    migrations/
tests/
```

Fluxo:

``` text
API
 ↓
Service
 ↓
Repository
 ↓
Database
```

## Organização do Frontend

``` text
src/
  components/
  pages/
  hooks/
  services/
  store/
  contexts/
  utils/
  types/
```

## Modelo Conceitual

Não armazenar apenas arquivos, mas sim **datasets**.

``` text
Empresa
  └── Datasets
        └── Tabelas
              ├── Colunas
              ├── Relacionamentos
              └── Registros
```

## Importação

Suportar: - CSV - Excel - ODS - JSON - SQL

Estrutura inicial:

``` text
uploads/
  empresa/
    dataset/
      arquivo.xlsx
```

No futuro substituir por armazenamento em S3.

## Catálogo de Dados

Cada coluna deve possuir: - Nome - Tipo - Descrição - Origem -
Responsável - Tags - Relacionamentos - Sinônimos - Última atualização -
Indicadores de qualidade

## Separação entre Metadados e Dados

### Banco de Metadados

-   Usuários
-   Workspaces
-   Datasets
-   Tabelas
-   Colunas
-   Relacionamentos
-   Histórico
-   Permissões

### Banco Operacional

-   Dados importados pelas empresas

Inicialmente ambos podem utilizar PostgreSQL.

## Roadmap

1.  Fundação
    -   Docker
    -   PostgreSQL
    -   FastAPI
    -   React
    -   Alembic
    -   SQLAlchemy
2.  Metamodelo
    -   Workspace
    -   Dataset
    -   Tabela
    -   Coluna
    -   Relacionamento
3.  Importação
    -   CSV
    -   Excel
    -   Inferência de tipos
    -   Pré-visualização
4.  Gerenciamento
    -   CRUD
    -   Relacionamentos
    -   Consultas
5.  Catálogo de Dados
    -   Documentação
    -   Tags
    -   Lineage
    -   Qualidade
6.  IA
    -   Camada semântica
    -   NL2SQL
    -   Uso dos metadados como contexto
    -   Insights empresariais

## Stack Final

-   Backend: Python, FastAPI, SQLAlchemy, Alembic, Pydantic
-   Banco: PostgreSQL
-   Frontend: React, TypeScript, Vite, TailwindCSS, Shadcn UI
-   Estado: Zustand
-   Dados: TanStack Query
-   Tabelas: TanStack Table
-   ETL: Pandas, Polars, OpenPyXL, PyArrow
-   Ferramentas: Docker, Docker Compose, Git, GitHub, DBeaver
-   Testes: Pytest
