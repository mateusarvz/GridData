# Fluxo De Dados

## Visão Geral

O sistema trabalha com dados em estágios.

### 1. Entrada

O usuário envia arquivos tabulares.

Tipos aceitos no fluxo atual:

- CSV
- XLSX
- XLS
- Parquet

### 2. Leitura

O backend usa pandas para interpretar o conteúdo.

### 3. Estatísticas

O sistema calcula:

- total de linhas
- total de valores nulos
- unicidade
- exemplos de valores
- candidatos a chave primária

### 4. Inferência

Com base nas estatísticas, o sistema sugere:

- tipo SQL por coluna
- possíveis relacionamentos
- estrutura inicial da tabela

### 5. Revisão

O usuário revisa os dados na interface.

Nessa etapa pode:

- alterar tipo de coluna
- aprovar ou rejeitar relacionamento
- adicionar relacionamento manual

### 6. Commit

Depois da confirmação:

- o backend gera SQL
- o SQL é executado
- staging é limpo
- a sessão é finalizada

## Armazenamento Temporário

O staging guarda:

- sessões
- tabelas
- relacionamentos
- linhas importadas

Essa camada existe para permitir revisão antes da gravação final.

## Persistência Final

A persistência final usa SQL gerado a partir da sessão aprovada.

O commit cria estruturas em `table_schema` e aplica vínculos aprovados.

## Rastreabilidade

O módulo de auditoria registra eventos como:

- criação de sessão
- inferência de schema
- criação de relacionamento
- commit final

Isso ajuda em rastreio operacional e análise posterior.

