# Dama Box

Plataforma web para análise, organização e revisão de estruturas de dados.

O sistema foi desenhado para receber arquivos tabulares, extrair metadados, sugerir tipos e relacionamentos, permitir revisão manual e gerar o SQL final para persistência.

## Visão Geral

O projeto combina:

- backend em FastAPI
- frontend em React
- integração com Supabase
- análise automatizada de schema
- suporte a revisão humana antes do commit

## O Que Este Projeto Faz

- autentica usuários
- gerencia sessão e contexto de tenant
- recebe arquivos CSV, XLSX, XLS e Parquet
- calcula estatísticas de colunas
- sugere tipos de dados
- identifica relacionamentos candidatos
- permite ajustes manuais
- gera SQL final para commit
- registra eventos relevantes em auditoria

## Estrutura

- `backend/`: API, regras de negócio, persistência e scripts
- `frontend/`: interface do usuário
- `docs/`: documentação funcional e técnica
- `backend/tests/`: testes automatizados

## Fluxo Principal

1. Usuário acessa a aplicação
2. Faz login
3. Envia arquivos de dados
4. Backend cria uma sessão de análise
5. Sistema processa colunas e relacionamentos
6. Usuário revisa o resultado
7. Commit final gera e executa SQL
8. Dados de staging são limpos

## Principais Áreas Técnicas

### Backend

Responsável por:

- autenticação
- banco de dados
- regras de domínio
- análise de schema
- auditoria
- integração com serviços externos

### Frontend

Responsável por:

- login
- upload de arquivos
- revisão do schema
- edição manual de colunas e relacionamentos
- navegação entre etapas

## Segurança

O repositório foi estruturado para manter informações sensíveis fora do Git.

Boas práticas adotadas:

- uso de arquivos `.env` locais
- exemplos separados em `.env.example`
- segredos fora do código-fonte
- `.gitignore` para ambientes, caches, logs e arquivos sensíveis

## Documentação

Arquivos de apoio em `docs/` explicam:

- visão geral do sistema
- arquitetura do backend
- arquitetura do frontend
- fluxo de execução
- módulos internos
- segurança e dados sensíveis
- fluxo de dados

## Tecnologias

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Supabase
- React
- TypeScript
- Vite

## Observação

Este projeto está organizado para uso corporativo, com separação clara entre interface, lógica de negócio, persistência e documentação.
