"""Detecção determinística de candidatos a relacionamento."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CandidatoFK:
    tabela_origem: str
    coluna_origem: str
    tabela_destino: str
    coluna_destino: str
    percentual_sobreposicao: float
    percentual_sobreposicao_inversa: float
    unica_origem: bool
    unica_destino: bool
    compatibilidade_nome: bool
    mesmo_nome: bool
    cardinalidade: str
    score: float
    valores_origem_amostra: list[str] = field(default_factory=list)
    valores_destino_amostra: list[str] = field(default_factory=list)
    ordem_origem: int = 0
    ordem_destino: int = 0

    def as_dict(self) -> dict:
        return {
            "tabela_origem": self.tabela_origem,
            "coluna_origem": self.coluna_origem,
            "tabela_destino": self.tabela_destino,
            "coluna_destino": self.coluna_destino,
            "percentual_sobreposicao": self.percentual_sobreposicao,
            "percentual_sobreposicao_inversa": self.percentual_sobreposicao_inversa,
            "unica_origem": self.unica_origem,
            "unica_destino": self.unica_destino,
            "compatibilidade_nome": self.compatibilidade_nome,
            "mesmo_nome": self.mesmo_nome,
            "cardinalidade": self.cardinalidade,
            "score": self.score,
            "valores_origem_amostra": self.valores_origem_amostra,
            "valores_destino_amostra": self.valores_destino_amostra,
            "ordem_origem": self.ordem_origem,
            "ordem_destino": self.ordem_destino,
        }

    def justificativa_fallback(self) -> str:
        partes: list[str] = []
        if self.compatibilidade_nome:
            partes.append(f"nome '{self.coluna_origem}' sugere FK para '{self.tabela_destino}'")
        if self.percentual_sobreposicao > 0:
            partes.append(
                f"{round(self.percentual_sobreposicao * 100)}% dos valores de '{self.coluna_origem}' existem em "
                f"'{self.tabela_destino}.{self.coluna_destino}'"
            )
        if self.unica_destino:
            partes.append("coluna destino única")
        return "; ".join(partes) or "heurística local"


def _nome_compativel(col_origem: str, nome_tabela_destino: str) -> bool:
    col_lower = col_origem.lower()
    tab_lower = nome_tabela_destino.lower()
    singulares = [tab_lower]
    for suf in ("es", "s"):
        if tab_lower.endswith(suf) and len(tab_lower) > len(suf) + 2:
            singulares.append(tab_lower[: -len(suf)])
    for singular in singulares:
        if col_lower in {
            f"{singular}_id",
            f"id_{singular}",
            f"{singular}id",
            f"fk_{singular}",
            f"{singular}_fk",
            f"codigo_{singular}",
            f"cod_{singular}",
        }:
            return True
    return False


def _unique_values(values: list[Any] | None) -> tuple[bool, list[str]]:
    clean = [str(v) for v in (values or []) if v is not None]
    if not clean:
        return False, []
    return len(clean) == len(set(clean)), clean[:10]


def detect_fk_candidates(tables: list[dict]) -> list[CandidatoFK]:
    candidatos: list[CandidatoFK] = []
    seen: set[tuple[str, str, str, str]] = set()

    for table_origem in tables:
        for idx_origem, col_origem in enumerate(table_origem["colunas"]):
            nome_origem = col_origem["nome"]
            nome_origem_lower = nome_origem.lower()
            origem_amostra = col_origem.get("amostra_fk") or col_origem.get("amostra") or []
            unica_origem, amostra_origem = _unique_values(origem_amostra)
            eh_id_origem = nome_origem_lower == "id"
            eh_fk_origem = (
                (nome_origem_lower.endswith("_id") and not eh_id_origem)
                or nome_origem_lower.startswith("id_")
                or nome_origem_lower.startswith("fk_")
                or nome_origem_lower.startswith("codigo_")
                or nome_origem_lower.startswith("cod_")
            )
            col_origem_pk = bool(col_origem.get("is_pk_candidate", False) or eh_id_origem)

            for table_destino in tables:
                if table_destino["nome_tabela"] == table_origem["nome_tabela"]:
                    continue

                for idx_destino, col_destino in enumerate(table_destino["colunas"]):
                    chave = (
                        table_origem["nome_tabela"],
                        nome_origem,
                        table_destino["nome_tabela"],
                        col_destino["nome"],
                    )
                    if chave in seen:
                        continue

                    nome_destino = col_destino["nome"]
                    nome_destino_lower = nome_destino.lower()
                    destino_amostra = col_destino.get("amostra_fk") or col_destino.get("amostra") or []
                    unica_destino, amostra_destino = _unique_values(destino_amostra)
                    destino_pk = bool(col_destino.get("is_pk_candidate", False) or nome_destino_lower == "id")

                    compat_nome = _nome_compativel(nome_origem, table_destino["nome_tabela"])
                    mesmo_nome = nome_origem_lower == nome_destino_lower

                    if not destino_pk:
                        continue
                    if not (compat_nome or mesmo_nome or (eh_fk_origem and destino_pk)):
                        continue

                    overlap = 0.0
                    overlap_inverso = 0.0
                    if amostra_origem and amostra_destino:
                        set_origem = set(amostra_origem)
                        set_destino = set(amostra_destino)
                        if set_origem:
                            overlap = len(set_origem & set_destino) / len(set_origem)
                        if set_destino:
                            overlap_inverso = len(set_origem & set_destino) / len(set_destino)

                    if unica_origem and unica_destino:
                        cardinalidade = "1:1"
                    elif not unica_origem and unica_destino:
                        cardinalidade = "N:1"
                    elif unica_origem and not unica_destino:
                        cardinalidade = "1:N"
                    else:
                        cardinalidade = "N:N"

                    score = 0.0
                    if idx_origem == 0 and idx_destino != 0:
                        score += 0.20
                    elif idx_origem != 0 and idx_destino == 0:
                        score += 0.05
                    if col_origem_pk and unica_origem:
                        score += 0.10
                    if not unica_origem and unica_destino:
                        score += 0.25
                    elif unica_origem and not unica_destino:
                        score += 0.10
                    if compat_nome:
                        score += 0.20
                    if mesmo_nome:
                        score += 0.25
                    if overlap >= 0.95:
                        score += 0.35
                    elif overlap >= 0.90:
                        score += 0.30
                    elif overlap >= 0.80:
                        score += 0.20
                    elif overlap >= 0.50:
                        score += 0.10
                    if overlap_inverso >= 0.90:
                        score += 0.05
                    if nome_origem_lower == "id":
                        score += 0.15

                    score = min(round(score, 3), 1.0)
                    if score < 0.50:
                        continue

                    seen.add(chave)
                    candidatos.append(
                        CandidatoFK(
                            tabela_origem=table_origem["nome_tabela"],
                            coluna_origem=nome_origem,
                            tabela_destino=table_destino["nome_tabela"],
                            coluna_destino=nome_destino,
                            percentual_sobreposicao=round(overlap, 3),
                            percentual_sobreposicao_inversa=round(overlap_inverso, 3),
                            unica_origem=unica_origem,
                            unica_destino=unica_destino,
                            compatibilidade_nome=compat_nome,
                            mesmo_nome=mesmo_nome,
                            cardinalidade=cardinalidade,
                            score=score,
                            valores_origem_amostra=amostra_origem,
                            valores_destino_amostra=amostra_destino,
                            ordem_origem=idx_origem,
                            ordem_destino=idx_destino,
                        )
                    )

    candidatos.sort(key=lambda c: c.score, reverse=True)
    return candidatos
