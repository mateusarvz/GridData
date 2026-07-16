# Arquitetura Do Frontend

## Objetivo

O frontend entrega a experiência operacional da plataforma.

Ele permite:

- login
- upload
- revisão de schema
- chat com Gemini
- navegação por workspace
- confirmação de commit

## Entrada Principal

O ponto de entrada visual está em `frontend/src/App.tsx`.

Esse arquivo:

- controla estado global da tela
- decide entre login, perfil e aplicação
- alterna entre abas principais
- coordena limpeza de sessão

## Fluxo De Tela

Existem três estados principais:

1. não autenticado
2. precisa completar perfil
3. autenticado

Depois de autenticado, o usuário vê o shell da aplicação.

## Estrutura Visual

Camadas principais:

- `AppShell`
- `Sidebar`
- `Topbar`
- views de conteúdo

Os componentes visuais ficam em:

- `frontend/src/components/layout/`
- `frontend/src/components/workspace/`
- `frontend/src/components/data-upload/`
- `frontend/src/components/schema-review/`
- `frontend/src/components/auth/`
- `frontend/src/components/gemini/`

## Estado Global

O frontend usa stores para estado compartilhado:

- `userStore`
- `workspaceStore`
- `dataSessionStore`

Essas stores evitam prop drilling excessivo.

## Serviços

`frontend/src/services/` concentra chamadas à API.

Arquivos importantes:

- `api.ts`
- `supabase.ts`
- `dataUpload.ts`
- `schemaAnalysis.ts`

Esses serviços fazem a ponte entre interface e backend.

## Integração Com Supabase

`frontend/src/utils/supabase.ts` e `frontend/src/services/supabase.ts` organizam a leitura de variáveis públicas de frontend.

O frontend usa apenas credenciais de navegação pública, nunca segredo administrativo.

## Views Mais Relevantes

### Login

`LoginScreen.tsx` controla entrada do usuário.

### Completar Perfil

`ProfileCompletionScreen.tsx` completa informações iniciais quando necessário.

### Upload

`DataUploadView.tsx` e componentes auxiliares tratam envio e pré-visualização.

### Revisão

`SchemaReviewView.tsx` e seus editores mostram:

- colunas
- relacionamentos
- SQL final

### Gemini

`GeminiChatView.tsx` oferece suporte de interação auxiliar.

## Fluxo De Navegação

`App.tsx` troca a tela ativa com base em `activeTab`.

As principais abas são:

- `upload`
- `gemini`
- `schema-review`

## Limpeza De Sessão

Ao fazer logout ou finalizar commit, o frontend:

- limpa dados temporários
- remove sessão local
- zera estados de upload
- volta para tela inicial

Isso evita persistência indevida de contexto antigo.

## Qualidade Da Interface

O projeto usa:

- TypeScript
- React
- Vite
- CSS moderno

A organização sugere foco em:

- componentes reutilizáveis
- separação clara de responsabilidades
- experiência guiada por etapas

