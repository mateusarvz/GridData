# 🖥️ Telas e Prompts do Sistema — Dama Box

Este arquivo centraliza as especificações de interface e os **prompts de engenharia** para o desenvolvimento progressivo do **Dama Box**, alinhados com a arquitetura descrita em `Arquitetura_Plataforma_Organizacao_Dados.md` e a visão geral do `README.md`.

---

## 📍 Tela 1: Workspace de Organização de Tabelas (Drag & Drop com Menu Flutuante)

### 🎯 Objetivo e Visão Conceitual
Esta é a **primeira tela operacional** do sistema (a evolução moderna do Dashboard / Acesso às Tabelas). Em vez de uma lista estática e sem graça, a proposta é um **Workspace Interativo e Dinâmico**, operando como um organizador visual de *datasets*.

Seguindo o princípio de **começar simples e incrementar com o tempo**, esta primeira versão foca na fundação da estrutura hierárquica:
* **Elementos iniciais:** Apenas **Pastas** (`Dataset / Grupo`) e **Tabelas** (`Data Entity`).
* **Hierarquia Livre:** Pastas podem armazenar outras pastas e tabelas recursivamente.
* **Interatividade Core:** Um **Menu Flutuante (Floating Dock)** na parte inferior da tela contendo os elementos arrastáveis ou acionáveis, acompanhado de navegação fluida (*breadcrumbs* / cards dinâmicos) e suporte a **Drag & Drop** (arrastar para criar, arrastar para reordenar e arrastar para dentro de pastas).

---

### 🎨 Requisitos de Design e Experiência do Usuário (UI/UX)
* **Estética Premium & Dark Mode Integrado:** Visual ultra-moderno com paleta de cores curada (fundo escuro profundo `slate-950`/`zinc-900`, acentos vibrantes em ciano/índigo/violeta), bordas sutis e tipografia limpa (Inter ou Outfit).
* **Glassmorphism no Menu Flutuante:** O dock inferior deve flutuar suavemente sobre a tela com efeito de vidro fosco (`backdrop-blur-md`, borda translúcida, sombra difusa).
* **Micro-animações (Framer Motion ou CSS Transitions):**
  * Suavidade ao abrir pastas e transicionar entre níveis de profundidade.
  * Efeito de *hover* dinâmico nos cards (elevação sutil, brilho na borda).
  * Feedback visual imediato durante o arrasto (*drop target* destacado com borda pontilhada ou cor de acento).
* **Empty State Convidativo:** Quando uma pasta (ou a raiz) estiver vazia, exibir uma ilustração/ícone elegante convidando o usuário a arrastar um elemento do menu flutuante ou clicar para criar.

---

### 🚀 O Prompt Completo (Pronto para Uso)

Abaixo está o prompt estruturado e de alta precisão para ser utilizado em geradores de código (IA, Lovable, Cursor, Claude Dev ou pelo próprio Antigravity) para construir esta primeira versão da tela em React + TypeScript + Tailwind CSS:

```markdown
<PROMPT_INICIAL_TELA_WORKSPACE>
# Tarefa: Desenvolver a Tela "Workspace de Tabelas com Drag & Drop e Menu Flutuante" do Dama Box

Você é um desenvolvedor Frontend Sênior e Especialista em UI/UX Design. Sua missão é criar a tela principal do **Dama Box** (Plataforma de Organização de Dados e Camada Semântica), onde o usuário modela e organiza visualmente suas tabelas e datasets.

## 1. Stack e Tecnologias Obrigatórias
- **Framework:** React com TypeScript e Vite.
- **Estilização:** Tailwind CSS (utilizando classes modernas, design responsivo, suporte nativo a Dark Mode moderno com tons escuros profundos e acentos vibrantes).
- **Ícones:** `lucide-react` (ícones limpos, modernos e semânticos).
- **Animações & Drag and Drop:** Utilize `@dnd-kit/core` + `@dnd-kit/sortable` (ou `framer-motion` / HTML5 DnD limpo e reativo) para garantir animações fluidas de arrastar e soltar sem bugs visuais.

## 2. Conceito e Funcionalidades Core (MVP Iterativo)
Nesta primeira versão, o sistema deve gerenciar uma árvore hierárquica livre composta por dois tipos de elementos:
1. 📁 **Pasta (Folder/Dataset):** Pode conter tabelas e também outras subpastas (aninhamento infinito).
2. 📊 **Tabela (Table):** Representa a entidade de dados onde futuramente residirão colunas e registros.

### A. Estrutura de Navegação (Breadcrumbs & Grid/List View)
- No topo da área principal, exiba uma barra de navegação tipo **Breadcrumb interativo** (ex: `🏠 Workspace > 📁 Financeiro > 📁 Vendas 2026`). O usuário pode clicar em qualquer item do caminho para voltar aos níveis anteriores.
- Apresente os elementos da pasta atual em um **Grid responsivo de Cards modernos** (com opção futura ou toggle para visualização em Lista).
- **Card de Pasta:** Ícone de pasta em destaque, nome da pasta, contador de itens internos (ex: "2 pastas, 4 tabelas"), data de modificação e menu de ações rápidas (Renomear, Excluir).
- **Card de Tabela:** Ícone de tabela (com cor ou badge distintiva), nome da tabela, breve descrição ou status ("Vazia / 0 colunas"), data de criação e menu de ações (Renomear, Excluir).
- Ao clicar duas vezes (ou clicar em "Abrir") em uma **Pasta**, o workspace transiciona suavemente para exibir o conteúdo interno dessa pasta.
- Ao clicar em uma **Tabela**, exiba por enquanto um modal ou painel lateral de "Pré-visualização da Tabela" (informando que a modelagem de colunas será conectada na próxima etapa).

### B. O Menu Flutuante (Floating Action Dock)
- Na parte inferior da tela, centralizado, implemente um **Menu Flutuante (Dock)** no estilo macOS / Glassmorphic (`backdrop-blur-lg bg-zinc-900/80 border border-white/10 shadow-2xl rounded-full px-6 py-3`).
- O Dock deve conter:
  - Botão/Draggable: **`+ 📁 Nova Pasta`**
  - Botão/Draggable: **`+ 📊 Nova Tabela`**
  - *(Opcional)* Input rápido ou botão de busca para filtrar itens na tela atual.
- **Dupla Interação:**
  1. **Clique Rápido:** Clicar em "Nova Pasta" ou "Nova Tabela" abre um modal simples ou inline para digitar o nome e cria o item na pasta atual.
  2. **Drag & Drop (Arrastar do Dock):** O usuário pode arrastar o ícone de "Nova Pasta" ou "Nova Tabela" do Dock e soltar diretamente na área de trabalho para criar no local, OU soltar sobre uma pasta existente para criar o item diretamente dentro daquela pasta!

### C. Drag and Drop Avançado e Intuitivo (Mover e Reordenar)
- **Mover para dentro de Pasta:** O usuário pode pegar um card existente no grid (ex: a tabela "Clientes") e arrastá-lo para cima do card de uma pasta (ex: "CRM"). A pasta de destino deve ganhar um destaque visual (*Hover state*: borda brilhante e leve escala) indicando o *Drop Target*. Ao soltar, a tabela é movida para dentro da pasta.
- **Reordenação:** Permita reorganizar visualmente a ordem das tabelas e pastas no grid através do arrasto.
- **Breadcrumb Drop:** Permita arrastar um item do grid atual e soltá-lo em um link anterior do *Breadcrumb* para movê-lo de volta para uma pasta pai!

### D. Gestão de Estado e Dados Mockados (Para Teste Imediato)
- Crie um estado global ou local limpo (utilizando `useState`/`useReducer` ou Zustand) com dados mockados iniciais ricos para que a tela já nasça viva e interativa.
- Exemplo de dados iniciais:
  - Pasta `📁 Gestão Financeira` (contendo tabela `📊 Fluxo de Caixa` e subpasta `📁 Auditoria 2025`).
  - Pasta `📁 Recursos Humanos` (contendo tabelas `📊 Funcionários` e `📊 Folha de Pagamento`).
  - Tabela raiz `📊 Clientes Ativos`.

## 3. Diretrizes de Design & Estética (Impeccable UI)
- **Aparência de Produto Premium:** A interface não pode parecer um "protótipo básico". Use gradientes sutis, sombras profundas e bordas semi-transparentes (`border-zinc-800`).
- **Animações Suaves:** Use transições para abertura de pastas, hover nos cards, surgimento do dock e exclusão de itens.
- **Empty State Excepcional:** Se uma pasta não tiver nenhum conteúdo, mostre uma área centralizada elegante com um ícone pontilhado e texto: *"Esta pasta está vazia. Arraste uma Pasta ou Tabela do menu inferior para começar a organizar seus dados."*
- **Acessibilidade & Atalhos:** Suporte a atalhos de teclado (ex: `F2` para renomear, `Del` para excluir, `Esc` para fechar modais).

## 4. O Que Entregar
- Código modular e limpo, dividindo em componentes lógicos: `WorkspaceCanvas`, `FloatingDock`, `FolderCard`, `TableCard`, `BreadcrumbNav`, `CreateModal` e o gerenciador de estado do Drag and Drop.
- Sem placeholders vazios ou TODOs quebrados; entregue a experiência funcional e visualmente impressionante no primeiro carregamento.
</PROMPT_INICIAL_TELA_WORKSPACE>
```

---

## 📈 Roadmap de Evolução da Tela (Próximos Incrementos)

Para manter o princípio de **"começar simples e ir incrementando"**, eis o planejamento dos próximos passos que serão acoplados a este Workspace:

| Etapa | Funcionalidade | Descrição |
| :--- | :--- | :--- |
| **Fase 2** | **Conexão com Editor de Colunas** | Ao clicar em uma Tabela, abrir o *Drawer* lateral para adicionar, remover e tipar colunas (Texto, Número, Data, FK, Arquivo) visualmente. |
| **Fase 3** | **Upload e Anexo de Arquivos (Drag to Folder)** | Adicionar o item "📄 Arquivo/Dataset (CSV/Excel)" no Menu Flutuante para permitir importar planilhas arrastando diretamente para as pastas. |
| **Fase 4** | **Modo Visão de Relacionamentos (Canvas 2D)** | Um botão de alternância (*Toggle*: `Grid View` <-> `Diagram View`) que transforma o grid em um canvas interativo onde as tabelas se conectam por linhas para formar Chaves Estrangeiras (FK). |
| **Fase 5** | **Customização Visual de Pastas e Tags** | Permitir ao usuário escolher cores personalizadas para os cards de pastas, ícones customizados e tags de categorização para filtragem rápida. |
