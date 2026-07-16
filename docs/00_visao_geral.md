# Visão Geral do Repositório

## Propósito

Este repositório implementa uma plataforma web para análise e organização de dados com foco em:

- upload de arquivos tabulares
- análise automática de estrutura
- sugestão de relacionamentos entre tabelas
- revisão manual de esquema
- geração de SQL de commit
- integração com autenticação e serviços externos

O sistema foi desenhado para trabalhar com dados em etapas:

1. o usuário entra na aplicação
2. envia arquivos de dados
3. o backend analisa colunas e relações
4. a interface mostra as sugestões
5. o usuário revisa e confirma
6. o sistema gera e executa SQL para persistir a estrutura

## Estrutura Principal

O projeto está dividido em dois blocos:

- `backend/`: API FastAPI e lógica de domínio
- `frontend/`: aplicação React com interface de usuário

Também existem:

- `docs/`: documentação funcional e técnica
- `backend/tests/`: testes automatizados
- `backend/scripts/`: scripts de banco e manutenção

## O Que O Sistema Faz

Em termos simples, o sistema:

- autentica usuários
- gerencia sessão do usuário
- recebe arquivos CSV, XLSX, XLS e Parquet
- calcula estatísticas de colunas
- infere tipos de dados
- tenta descobrir chaves estrangeiras candidatas
- usa Gemini para sugerir esquema
- permite edição manual antes do commit
- gera SQL final para persistência
- mantém histórico e auditoria

## Conceito Central

O conceito mais importante do projeto é a separação entre:

- dados enviados pelo usuário
- análise intermediária
- confirmação manual
- persistência final

Isso evita salvar estrutura prematuramente e dá controle ao usuário antes do commit.

## Componentes De Alto Nível

- `backend/app/main.py`: cria a aplicação FastAPI e registra rotas
- `backend/app/core/`: configuração, segurança, banco e integração com Supabase
- `backend/app/modules/`: módulos de negócio organizados por domínio
- `frontend/src/App.tsx`: controla fluxo visual principal
- `frontend/src/components/`: telas e blocos de interface
- `frontend/src/services/`: chamadas HTTP e integrações
- `frontend/src/store/`: estado global da interface

## Fluxo Resumido

1. Frontend carrega e verifica status do backend e do Supabase
2. Usuário faz login
3. Sessão é armazenada no estado da aplicação
4. Usuário envia arquivos
5. Backend cria sessão de análise
6. Sistema extrai metadados e salva dados de staging
7. Gemini e regras internas sugerem estrutura
8. Usuário revisa na tela de schema
9. Commit gera e executa SQL final

## Observação Sobre Segurança

Este repositório deve ser usado com:

- variáveis de ambiente
- arquivos `.env` fora do Git
- segredos nunca versionados
- credenciais locais separadas de exemplos

## Como Ler A Documentação

Os próximos arquivos explicam:

- arquitetura do backend
- arquitetura do frontend
- fluxo de autenticação
- fluxo de upload e análise
- regras de segurança e dados sensíveis
- papel de cada módulo

