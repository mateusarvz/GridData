# Segurança E Dados Sensíveis

## Regra Geral

Nenhuma credencial, segredo ou arquivo local sensível deve ir para o Git.

Isso vale para:

- `.env`
- backups
- bancos locais
- chaves privadas
- arquivos de certificado
- diretórios de ambiente virtual

## O Que Deve Ficar Fora Do Repositório

- arquivos `.env`
- `venv`, `.venv`, `env`
- `node_modules`
- logs
- arquivos `.db`, `.sqlite`, `.sqlite3`
- chaves `.pem`, `.key`, `.p12`, `.pfx`
- dumps e backups

## O Que Pode Existir No Repositório

- arquivos `.env.example`
- documentação
- código-fonte
- scripts sem segredos
- testes

## Como O Projeto Usa Segredos

O backend lê configuração por ambiente em `backend/app/core/config.py`.

O frontend lê apenas variáveis públicas, como:

- URL do projeto
- chave anônima de cliente

O backend pode usar segredos administrativos, mas eles devem vir do ambiente local ou do servidor.

## Riscos Já Cobertos

O projeto tinha exemplos com valores reais ou muito próximos de segredo.

Agora a abordagem correta é:

- usar placeholders nos exemplos
- ler valores reais de ambiente
- nunca versionar credenciais

## Recomendações Operacionais

1. criar `.env` localmente em cada ambiente
2. manter `.env.example` como referência
3. rotacionar qualquer segredo que já tenha sido exposto
4. revisar `git status` antes de cada commit
5. evitar colocar segredo em código, teste ou script

## Sobre `.gitignore`

O `.gitignore` protege apenas arquivos novos ou ainda não versionados.

Se um segredo já entrou no Git antes:

- ele continua no histórico
- precisa ser removido do histórico ou substituído
- a chave deve ser rotacionada

## Boas Práticas Para Este Projeto

- usar variáveis de ambiente para senhas e tokens
- usar placeholders em documentação
- separar segredo administrativo de configuração pública
- revisar exemplos antes de publicar
- manter arquivos locais fora do controle de versão

