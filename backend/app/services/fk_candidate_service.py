"""
Detecção determinística de candidatos a chave estrangeira.

Roda no backend ANTES de chamar o Gemini.
Combina dois sinais:
  1. Compatibilidade de nome (xxx_id → tabela xxx)
  2. Sobreposição de valores nas amostras FK armazenadas

Os candidatos são enviados ao Gemini como contexto adicional —
o Gemini valida, complementa com análise semântica e retorna a
confiança final + justificativa.

Se o Gemini falhar (ex: 429), os candidatos com score ≥ 0.5 são
usados diretamente como relacionamentos (sem a validação semântica).
"""
from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Estrutura de dados
# ---------------------------------------------------------------------------

@dataclass
class CandidatoFK:
    tabela_origem: str          # Tabela com a FK (ex: pedidos)
    coluna_origem: str          # Coluna FK (ex: cliente_id)
    tabela_destino: str         # Tabela referenciada (ex: clientes)
    coluna_destino: str         # Coluna PK referenciada (ex: id)
    percentual_sobreposicao: float  # Fração dos valores FK presentes na PK
    compatibilidade_nome: bool  # True se nome segue padrão entidade_id
    score: float                # Score composto 0.0–1.0

    def as_dict(self) -> dict:
        return {
            "tabela_origem": self.tabela_origem,
            "coluna_origem": self.coluna_origem,
            "tabela_destino": self.tabela_destino,
            "coluna_destino": self.coluna_destino,
            "percentual_sobreposicao": self.percentual_sobreposicao,
            "compatibilidade_nome": self.compatibilidade_nome,
            "score": self.score,
        }

    def justificativa_fallback(self) -> str:
        partes = []
        if self.compatibilidade_nome:
            partes.append(f"nome '{self.coluna_origem}' segue padrão FK para '{self.tabela_destino}'")
        if self.percentual_sobreposicao > 0:
            perc = round(self.percentual_sobreposicao * 100)
            partes.append(f"{perc}% dos valores de '{self.coluna_origem}' presentes em '{self.tabela_destino}.{self.coluna_destino}'")
        return "; ".join(partes) or "heurística de nome de coluna"


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _nome_compativel(col_origem: str, nome_tabela_destino: str) -> bool:
    """
    True se col_origem sugere FK para nome_tabela_destino.

    Reconhece padrões:
      - <tabela>_id   (ex: cliente_id → clientes)
      - id_<tabela>   (ex: id_cliente → clientes)
      - <tabela>id    (ex: clienteid → clientes)
      - fk_<tabela>   (ex: fk_cliente → clientes)
    """
    col_lower = col_origem.lower()
    tab_lower = nome_tabela_destino.lower()

    # Gera variações singulares removendo sufixos plurais comuns
    singulares: list[str] = [tab_lower]
    for suf in ("es", "s"):
        if tab_lower.endswith(suf) and len(tab_lower) > len(suf) + 2:
            singulares.append(tab_lower[: -len(suf)])

    for singular in singulares:
        if col_lower in (
            f"{singular}_id",
            f"id_{singular}",
            f"{singular}id",
            f"fk_{singular}",
            f"{singular}_fk",
            f"codigo_{singular}",
            f"cod_{singular}",
        ):
            return True
    return False


def _compute_overlap(pk_values: set[str], fk_values: set[str]) -> float:
    """
    Fração dos valores FK contidos no conjunto PK.

    overlap = |FK ∩ PK| / |FK|

    > 0.8 → forte evidência de FK
    > 0.5 → evidência moderada
    """
    if not fk_values or not pk_values:
        return 0.0
    return len(fk_values & pk_values) / len(fk_values)


# ---------------------------------------------------------------------------
# Detecção principal
# ---------------------------------------------------------------------------

def detect_fk_candidates(
    tables: list[dict],
) -> list[CandidatoFK]:
    """
    Encontra candidatos a relacionamento FK entre tabelas da mesma sessão.

    Args:
        tables: lista de dicts com estrutura:
            {
                "nome_tabela": str,
                "colunas": [
                    {
                        "nome": str,
                        "is_pk_candidate": bool,
                        "amostra_fk": list[str] | None,
                        ...
                    }
                ]
            }

    Returns:
        Lista de CandidatoFK ordenada por score desc (maiores evidências primeiro).
    """
    candidatos: list[CandidatoFK] = []
    seen: set[tuple] = set()

    # Pré-indexar: (nome_tabela, nome_col) → coluna data
    col_index: dict[tuple[str, str], dict] = {}
    for table in tables:
        for col in table["colunas"]:
            col_index[(table["nome_tabela"], col["nome"])] = col

    for table_orig in tables:
        for col_orig in table_orig["colunas"]:
            col_nome = col_orig["nome"]
            col_lower = col_nome.lower()

            # Só analisa colunas que podem ser FK (não analisa 'id' como origem)
            eh_possivel_fk = (
                col_lower.endswith("_id") and col_lower != "id"
                or col_lower.startswith("id_")
                or col_lower.startswith("fk_")
                or col_lower.startswith("codigo_")
                or col_lower.startswith("cod_")
            )

            for table_dest in tables:
                if table_dest["nome_tabela"] == table_orig["nome_tabela"]:
                    continue

                for col_dest in table_dest["colunas"]:
                    chave = (
                        table_orig["nome_tabela"], col_nome,
                        table_dest["nome_tabela"], col_dest["nome"],
                    )
                    if chave in seen:
                        continue

                    compat_nome = _nome_compativel(col_nome, table_dest["nome_tabela"])
                    nomes_iguais = col_nome.lower() == col_dest["nome"].lower()
                    destino_eh_pk = (
                        col_dest.get("is_pk_candidate", False)
                        or col_dest["nome"].lower() == "id"
                    )

                    # Precisa de pelo menos compatibilidade de nome OU (coluna FK + destino PK)
                    if not compat_nome and not (eh_possivel_fk and destino_eh_pk):
                        continue
                    if not compat_nome:
                        continue  # Sem compatibilidade de nome, não gera candidato
                    if not destino_eh_pk:
                        continue  # FK válida precisa apontar para PK/ID

                    # Calcular sobreposição de valores (se amostras disponíveis)
                    perc_overlap = 0.0
                    amostra_orig = col_orig.get("amostra_fk")
                    amostra_dest = col_dest.get("amostra_fk")

                    if amostra_orig and amostra_dest:
                        set_pk = set(str(v) for v in amostra_dest)
                        set_fk = set(str(v) for v in amostra_orig)
                        perc_overlap = _compute_overlap(set_pk, set_fk)

                    # Score composto
                    score = 0.0
                    if compat_nome:
                        score += 0.60  # Sinal principal
                    if perc_overlap >= 0.80:
                        score += 0.35
                    elif perc_overlap >= 0.50:
                        score += 0.20
                    elif perc_overlap >= 0.20:
                        score += 0.10
                    if destino_eh_pk:
                        score += 0.05
                    if nomes_iguais and destino_eh_pk:
                        score = 1.0
                    score = min(round(score, 3), 1.0)

                    if score < 0.50:
                        continue  # Descarta candidatos fracos

                    seen.add(chave)
                    candidatos.append(CandidatoFK(
                        tabela_origem=table_orig["nome_tabela"],
                        coluna_origem=col_nome,
                        tabela_destino=table_dest["nome_tabela"],
                        coluna_destino=col_dest["nome"],
                        percentual_sobreposicao=round(perc_overlap, 3),
                        compatibilidade_nome=compat_nome,
                        score=score,
                    ))

    candidatos.sort(key=lambda c: c.score, reverse=True)
    return candidatos
