# Especificação de Autenticação, Segurança e Autorização (Auth + RBAC/ACL) — Dama Box

Este documento estabelece a especificação técnica de segurança de nível corporativo (*Enterprise-Grade*) para o **Dama Box**. Ele detalha os protocolos de autenticação, ciclo de vida dos tokens (JWT + Refresh Tokens rotativos), transporte seguro em navegadores, rotação de chaves, troca dinâmica de escopo de empresa (*Tenant Switching*) e a interceptação de autorização granular (RBAC + ACL) na camada de API (FastAPI).

---

## 1. Princípios de Segurança e Zero-Trust

1. **Backend como Única Autoridade Zero-Trust:** O Frontend nunca toma decisões de autorização de segurança. A ocultação de botões, abas ou tabelas no React é puramente uma conveniência de interface (UX). Toda requisição HTTP para a API deve ser autenticada e revalidada pelo Backend perante a modelagem de permissões.
2. **Blindagem contra Vetores OWASP Top 10:**
   *   **XSS (Cross-Site Scripting):** Refresh Tokens de longa duração **nunca** são retornados no corpo de requisições JSON nem acessíveis pelo `localStorage` / `sessionStorage`. São transportados exclusivamente via Cookies bloqueados para leitura por JavaScript (`HttpOnly`).
   *   **CSRF (Cross-Site Request Forgery):** Aplicação estrita da política `SameSite=Strict` e verificação de cabeçalhos CORS restritos a domínios autorizados.
   *   **Broken Access Control:** Injeção programática e obrigatória da chave do Tenant (`company_id`) e consulta sistemática à ACL Granular para recursos específicos.

---

## 2. Ciclo de Vida dos Tokens e Transporte Seguro

A plataforma adota uma arquitetura de **Tokens Híbridos de Dupla Camada**, separando sessões de curta duração de acessos de longo prazo para conciliar alta performance sem consultas ao banco em cada rota protegida (stateless JWT) e revogação imediata em emergências (stateful Refresh Tokens).

### 2.1. Estrutura e Payload do Access Token (`JWT`)
*   **Formato:** JSON Web Token assinado criptograficamente com algoritmo assimétrico **ED25519** ou **RS256** (chaves privadas no AWS Secrets Manager).
*   **Validade:** **10 minutos** a partir da emissão.
*   **Transporte:** Cabeçalho HTTP padrão: `Authorization: Bearer <eyJhbGciOi...>`
*   **Exemplo de Payload Decodificado:**
    ```json
    {
      "sub": "usr_01h87g6f5e4d3c2b1a000000",
      "email": "davi.silva@empresa.com",
      "username": "davi.silva",
      "cid": "comp_0015",
      "role": "Owner",
      "ver": true,
      "iat": 1783451000,
      "exp": 1783451600,
      "iss": "https://auth.damabox.com",
      "aud": "https://api.damabox.com"
    }
    ```
    *Legenda:* `sub` (ID global do usuário), `cid` (Company ID ativa no escopo atual), `role` (Cargo do usuário naquela empresa), `ver` (E-mail verificado), `exp` (Timestamp de expiração).

### 2.2. Estrutura e Armazenamento do Refresh Token
*   **Formato:** String aleatória criptograficamente segura de alta entropia (256 bits hexadecimais ou Base64URL). **Não é um JWT**.
*   **Validade:** **30 dias corridos** (renovado rotativamente a cada uso).
*   **Transporte:** Cookie HTTP Seguro com os seguintes atributos rigorosos:
    ```http
    Set-Cookie: damabox_refresh_token=rft_998877665544332211; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000
    ```
*   **Segurança no Banco (Proteção contra Exfiltração):** O valor em texto plano do Refresh Token **nunca é armazenado no banco de dados (`sistema.refresh_tokens`)**. O sistema calcula o hash SHA-256 (`hashlib.sha256(token.encode()).hexdigest()`) e armazena apenas a assinatura de hash. Em caso de roubo do banco de dados, os atacantes não conseguem forjar sessões válidas.

---

## 3. Fluxos de Autenticação e Rotação (Mermaid Sequence Diagrams)

### 3.1. Fluxo de Autenticação e Login Inicial

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário (Browser)
    participant API as API FastAPI
    database DB as Banco "sistema"

    User->>API: POST /api/v1/auth/login <br> {email, password, remember_me}
    API->>DB: SELECT * FROM users WHERE email = :email
    DB-->>API: Retorna hash da senha e failed_attempts
    API->>API: Valida Hash (Argon2id / BCrypt)
    
    alt Senha Inválida
        API->>DB: Incrementa failed_login_attempts
        API-->>User: 401 Unauthorized ("Credenciais Inválidas")
    else Senha Válida
        API->>DB: SELECT * FROM organization_members <br> WHERE user_id = :id AND is_active = true
        DB-->>API: Retorna lista de empresas e cargos (Pega empresa padrão/última)
        API->>API: Gera Access Token JWT (10 min, escopado na Empresa 15)
        API->>API: Gera Refresh Token Opaco e calcula SHA-256
        API->>DB: INSERT INTO refresh_tokens (token_hash, user_id, expires_at)
        API->>DB: Zera failed_login_attempts e atualiza last_login_at
        API-->>User: 200 OK + Payload JSON { access_token, user_info } <br> + Header Set-Cookie (HttpOnly Refresh Token)
    end
```

### 3.2. Fluxo de Rotação Segura do Refresh Token (Token Rotation)

Para mitigar roubos de cookies via ataques de rede, toda chamada ao endpoint de renovação invalida o token usado e emite um novo par (*Refresh Token Rotation* com detecção de reuso).

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário (Browser)
    participant API as API FastAPI
    database DB as Banco "sistema"

    Note over User,API: Access Token expirou no Frontend após 10 minutos
    User->>API: POST /api/v1/auth/refresh <br> (Envia Cookie HttpOnly automaticamente)
    API->>API: Extrai cookie damabox_refresh_token e calcula SHA-256
    API->>DB: SELECT * FROM refresh_tokens WHERE token_hash = :hash
    
    alt Token Não Encontrado ou Revogado (Possível Ataque de Reuso!)
        API->>DB: UPDATE refresh_tokens SET is_revoked = true <br> WHERE user_id = :suspect_user_id (REVOGA TUDO DO USUÁRIO)
        API-->>User: 401 Unauthorized + Limpa Cookie (Força novo login)
    else Token Válido e Ativo
        API->>DB: UPDATE refresh_tokens SET is_revoked = true WHERE id = :old_id
        API->>API: Gera NOVO Access Token JWT (10 min) e NOVO Refresh Token
        API->>DB: INSERT INTO refresh_tokens (novo_hash, user_id, expires_at)
        API-->>User: 200 OK { access_token } + Novo Cookie Set-Cookie
    end
```

---

## 4. Troca Dinâmica de Escopo de Empresa (Tenant Switching)

Como um usuário pode pertencer a múltiplas empresas (ex: `Owner` em `comp_0001` e `Guest` em `comp_0002`), o token JWT é sempre escopado em uma única empresa por vez para impedir que permissões de uma empresa vazem em chamadas à outra.

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário (Browser)
    participant API as API FastAPI
    database DB as Banco "sistema"

    Note over User: Logado na Empresa 15. Quer alternar para Empresa 22.
    User->>API: POST /api/v1/auth/switch-tenant <br> Header: Bearer <jwt_empresa_15> <br> Body: { "target_company_id": "comp_0022" }
    API->>API: Extrai sub (user_id) do JWT atual
    API->>DB: SELECT * FROM organization_members <br> WHERE user_id = :sub AND company_id = 'comp_0022' AND is_active = true
    
    alt Vínculo Não Existe ou Inativo
        API-->>User: 403 Forbidden ("Você não é membro desta organização")
    else Vínculo Válido (Ex: Cargo = Admin)
        API->>API: Gera NOVO Access Token JWT contendo: <br> cid = 'comp_0022', role = 'Admin'
        API-->>User: 200 OK { access_token: <novo_jwt_empresa_22> }
    end
    Note over User: Frontend substitui JWT em memória e recarrega Workspace
```

---

## 5. Modelagem e Interceptação no FastAPI (RBAC + ACL)

A autorização é avaliada em tempo de execução através do sistema de Injeção de Dependências (*Dependency Injection*) do FastAPI, interceptando as requisições antes que alcancem as funções de rota (*Route Handlers*).

### 5.1. Fluxograma Lógico de Avaliação de Acesso

```mermaid
flowchart TD
    Req[Requisição HTTP API] --> DepAuth[Dependência: get_current_user]
    DepAuth --> ValJWT{JWT Válido <br> e Não Expirado?}
    ValJWT -->|Não| Err401[401 Unauthorized]
    ValJWT -->|Sim| ExtCtx[Extrai do JWT:<br>user_id, cid e role]
    
    ExtCtx --> DepPerm[Dependência: require_permission]
    DepPerm --> IsAdmin{Role organizacional <br> é Owner ou Admin?}
    
    IsAdmin -->|Sim| Allow[200 OK - Acesso Total Concedido]
    IsAdmin -->|Não| IsGeneric{É rota genérica sem ID<br>ex: listar workspaces?}
    
    IsGeneric -->|Sim| CheckRBAC{Role Member/Guest tem<br>permissão genérica no RBAC?}
    CheckRBAC -->|Sim| Allow
    CheckRBAC -->|Não| Err403[403 Forbidden]
    
    IsGeneric -->|Não| GetRes[Extrair resource_id e resource_type da URL<br>ex: /tables/{table_id}]
    GetRes --> ConsultACL[Consulta Banco do Cliente:<br>SELECT FROM access_control_lists<br>WHERE resource_id = :id AND user_id = :user_id]
    
    ConsultACL --> HasACL{Existe regra ACL<br>explícita para este usuário?}
    HasACL -->|Sim| EvalACL{Permissão na ACL >=<br>Ação Requerida?}
    EvalACL -->|Sim| Allow
    EvalACL -->|Não| Err403
    
    HasACL -->|Não| FallbackRBAC{Fallback para RBAC:<br>Ação permitida para a role?}
    FallbackRBAC -->|Sim| Allow
    FallbackRBAC -->|Não| Err403
```

### 5.2. Padrão de Implementação no FastAPI (`backend/app/api/deps.py`)

O código abaixo ilustra a modelagem arquitetural para verificação de autorização em rotas protegidas:

```python
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Annotated, Optional
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class TokenPayload(BaseModel):
    sub: uuid.UUID
    email: str
    cid: uuid.UUID
    role: str

async def get_current_user_token(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenPayload:
    try:
        payload_dict = jwt.decode(token, "SECRET_KEY_FROM_SECRETS_MANAGER", algorithms=["ED25519", "RS256"])
        return TokenPayload(**payload_dict)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.")

class RequirePermission:
    """
    Dependência parametrizada para validar RBAC e ACL Granular.
    Exemplo de uso em rota: @app.put("/tables/{table_id}", dependencies=[Depends(RequirePermission("table:alter_schema"))])
    """
    def __init__(self, action: str, resource_id_param: Optional[str] = None):
        self.action = action
        self.resource_id_param = resource_id_param

    async def __call__(self, request: Request, token: Annotated[TokenPayload, Depends(get_current_user_token)]):
        # 1. Superusuários da empresa passam direto
        if token.role in ("Owner", "Admin"):
            return token

        # 2. Verificar se a rota tem um recurso específico alvo de ACL (ex: table_id)
        resource_id = None
        if self.resource_id_param and self.resource_id_param in request.path_params:
            resource_id = request.path_params[self.resource_id_param]

        if resource_id:
            # 3. Consultar ACL Granular no banco do Tenant daquela empresa (empresa_XXXX)
            # A conexão do tenant é obtida via middleware que usou token.cid
            db_tenant = request.state.db_tenant
            acl_rule = await db_tenant.execute(
                "SELECT permission_level FROM access_control_lists WHERE resource_id = :rid AND user_id = :uid",
                {"rid": resource_id, "uid": token.sub}
            )
            acl_level = acl_rule.scalar_one_or_none()
            
            if acl_level:
                # Se existe ACL, ela é soberana. Avaliar se o nível (ex: EDITOR) cobre a ação
                if self._check_acl_level(acl_level, self.action):
                    return token
                else:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ACL da tabela nega esta ação.")

        # 4. Fallback para verificação padrão de RBAC se não houve ACL específica
        if not self._check_rbac_fallback(token.role, self.action):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sua role na organização não permite esta ação.")
        
        return token
```

---

## 6. Políticas Complementares de Endpoints e Bloqueio

1. **Bloqueio de Força Bruta (Brute Force Protection):**
   *   Mantido na tabela `users` (`failed_login_attempts` e `locked_until`).
   *   Ao atingir 5 falhas contínuas no endpoint `POST /api/v1/auth/login`, o atributo `locked_until` é ajustado para `now() + 15 minutes`. Qualquer chamada com e-mail bloqueado retorna instantaneamente erro `429 Too Many Requests` com cabeçalho `Retry-After: 900`, sem consumir processamento de hash Argon2id/BCrypt.
2. **Encerramento Global de Sessões (Kill Switch / Revogação em Massa):**
   *   O endpoint `POST /api/v1/auth/logout-all-devices` altera `is_revoked = TRUE` para **todos** os registros do usuário em `sistema.refresh_tokens`. Em até 10 minutos (tempo máximo de expiração do JWT ativo na memória do browser), o usuário será compulsoriamente desconectado em todos os computadores, celulares e tablets simultaneamente.
3. **Cabeçalhos de Segurança Obrigatórios na API:**
   ```http
   Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
   X-Content-Type-Options: nosniff
   X-Frame-Options: DENY
   Content-Security-Policy: default-src 'self'; frame-ancestors 'none';
   ```
