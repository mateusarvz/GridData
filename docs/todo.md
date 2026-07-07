# 🗺️ Roadmap de Documentação e Planejamento — Dama Box

Painel de controle das etapas de design, especificação técnica e planejamento do software antes da implementação do código.

---

## 📋 Quadro de Tarefas (Checklist)

### 📌 Fase 1: Fundações, Domínio e Dados
- [x] **Documento de Regras de Negócio**
  - *Status:* Concluído em [regras_de_negocio.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/regras_de_negocio.md). Define a "constituição" e limites da plataforma.
- [x] **Arquitetura Multi-Tenancy (Isolamento de Banco)**
  - *Status:* Concluído em [arquitetura_multitenancy.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/arquitetura_multitenancy.md). Define a estratégia física de banco por cliente e roteamento dinâmico.
- [x] **Modelo de Domínio (DDD)**
  - *Status:* Concluído em [modelo_dominio_ddd.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/modelo_dominio_ddd.md). Define contextos delimitados, agregados (com Record incluso) e value objects.
- [x] **Diagrama ER Completo (PostgreSQL)**
  - *Status:* Concluído em [diagrama_er_postgresql.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/diagrama_er_postgresql.md). Contém diagramas Mermaid e scripts DDL reais para o banco sistema e banco cliente.

### 📌 Fase 2: Segurança, Autenticação e Autorização
- [x] **Especificação de Autenticação (Auth)**
  - *Status:* Concluído em [especificacao_auth_seguranca.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/especificacao_auth_seguranca.md). Define JWT 10min, Refresh Tokens rotativos em cookie HttpOnly e Tenant Switching.
- [x] **Modelagem RBAC + ACL Granular**
  - *Status:* Concluído em [especificacao_auth_seguranca.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/especificacao_auth_seguranca.md). Define fluxo de resolução RBAC vs ACL e injeção de dependência no FastAPI.

### 📌 Fase 3: Arquitetura de Software e API
- [x] **Clean Architecture no Backend**
  - *Status:* Concluído em [arquitetura_backend_api_rest.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/arquitetura_backend_api_rest.md). Define 4 camadas por módulo, DIP e Unit of Work (SQLAlchemy 2.0).
- [x] **Especificação REST / OpenAPI (Swagger)**
  - *Status:* Concluído em [arquitetura_backend_api_rest.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/arquitetura_backend_api_rest.md). Define catálogo de rotas, payloads JSON canônicos e padrão de erros RFC 7807.

### 📌 Fase 4: Operações, Auditoria e Ciclo de Vida
- [x] **Estratégia de Versionamento e Auditoria de Dados**
  - *Status:* Concluído em [estrategia_versionamento_migracoes.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/estrategia_versionamento_migracoes.md). Define JSON diffing para Time Travel e separação de logs por compliance.
- [x] **Estratégia de Migrações (Alembic)**
  - *Status:* Concluído em [estrategia_versionamento_migracoes.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/estrategia_versionamento_migracoes.md). Contém script runner customizado em AsyncIO/SQLAlchemy para migrações paralelas multi-tenant.

### 📌 Fase 5: Execução do Código e Implementação (Roadmap Executivo)
- [ ] **Plano de Codificação e TDD no Backend**
  - *Status:* Definido em [plano_codificacao.md](file:///c:/Users/davij/Desktop/Dama/dama-box/docs/plano_codificacao.md). Divide o desenvolvimento em 6 etapas cronológicas (Scaffolding Core, IAM, Catalog, Engine JSONB, Time Travel e Automação Multi-Tenant).

---

## 📚 Referências de Projeto
- **Template "Superpowers" da Stone:** Template de arquitetura corporativa, documentação e fluxos de excelência como padrão de engenharia.
  - *Endereço:* [github.com/obra/superpowers](https://github.com/obra/superpowers)