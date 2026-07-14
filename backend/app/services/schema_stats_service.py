"""
Cálculo de estatísticas descritivas por coluna a partir de um DataFrame pandas.

Chamado no momento do upload (CriarSessaoUseCase) — os resultados são
gravados no JSONB colunas_schema em schema_analysis_tables e usados depois
pelo InferirSchemaUseCase para enriquecer o payload do Gemini e calcular
candidatos a FK sem precisar re-ler os arquivos originais.
"""
import random
from typing import Any

import pandas as pd

from app.services.data_masking_service import is_sensitive_col, mask_samples

# Limite de amostras únicas armazenadas para detecção de overlap (backend only)
_MAX_AMOSTRA_FK = 200
# Limite de exemplos enviados ao Gemini
_MAX_EXEMPLOS_GEMINI = 8


def _safe_stat(func):
    """Wrapper silencia erros de stat em colunas com tipos inesperados."""
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            return None
    return inner


def compute_col_stats(series: pd.Series, col_name: str) -> dict[str, Any]:
    """
    Calcula estatísticas de uma única coluna.

    Retorna dict com:
      tipo_bruto, valores_nulos, percentual_nulos, valores_unicos,
      percentual_unicidade, is_pk_candidate, exemplos_gemini, amostra_fk (ou None)
    """
    total = len(series)
    nulos = int(series.isna().sum())
    nao_nulos = total - nulos
    unicos = int(series.nunique(dropna=True))

    perc_nulos = round(nulos / total, 4) if total > 0 else 0.0
    perc_unicidade = round(unicos / nao_nulos, 4) if nao_nulos > 0 else 0.0

    # Candidata a PK: ≥ 95% únicos, ≤ 5% nulos, pelo menos 1 valor distinto
    is_pk = perc_unicidade >= 0.95 and perc_nulos <= 0.05 and unicos > 0

    stats: dict[str, Any] = {
        "tipo_bruto": str(series.dtype),
        "valores_nulos": nulos,
        "percentual_nulos": perc_nulos,
        "valores_unicos": unicos,
        "percentual_unicidade": perc_unicidade,
        "is_pk_candidate": is_pk,
    }

    # Estatísticas numéricas
    if pd.api.types.is_numeric_dtype(series):
        non_null = series.dropna()
        if len(non_null) > 0:
            stats["valor_min"] = _safe_stat(lambda: str(non_null.min()))()
            stats["valor_max"] = _safe_stat(lambda: str(non_null.max()))()
            stats["media"] = _safe_stat(lambda: round(float(non_null.mean()), 4))()

    sensivel = is_sensitive_col(col_name)

    # Amostra aleatória para Gemini (mascarada se sensível)
    valores_nao_nulos: list[Any] = series.dropna().tolist()
    if sensivel:
        stats["exemplos_gemini"] = ["[valor mascarado - possível dado sensível]"]
    else:
        if len(valores_nao_nulos) > _MAX_EXEMPLOS_GEMINI:
            amostra_raw = random.sample(valores_nao_nulos, _MAX_EXEMPLOS_GEMINI)
        else:
            amostra_raw = valores_nao_nulos[:]
        stats["exemplos_gemini"] = mask_samples(col_name, amostra_raw, max_values=_MAX_EXEMPLOS_GEMINI)

    # Amostra de valores únicos para detecção de overlap (NUNCA enviada ao Gemini diretamente)
    if sensivel:
        stats["amostra_fk"] = None  # Colunas sensíveis não participam de overlap por valor
    else:
        unique_vals: list[Any] = series.dropna().unique().tolist()
        if len(unique_vals) > _MAX_AMOSTRA_FK:
            unique_vals = random.sample(unique_vals, _MAX_AMOSTRA_FK)
        stats["amostra_fk"] = [str(v) for v in unique_vals]

    return stats


def compute_table_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Gera lista de colunas enriquecidas com estatísticas para um DataFrame.

    Substitui _colunas_from_df — compatível com o mesmo schema JSONB
    (preserva todos os campos existentes e adiciona os novos).
    """
    result: list[dict[str, Any]] = []
    for col in df.columns:
        col_stats = compute_col_stats(df[col], col)
        entry: dict[str, Any] = {
            # Campos originais (compatibilidade com colunas_schema existente)
            "nome": col,
            "tipo_bruto": col_stats["tipo_bruto"],
            "tipo_sugerido": "",
            "nulo_permitido": bool(df[col].isna().any()),
            "editado_pelo_usuario": False,
            # Campos novos de estatísticas
            "valores_nulos": col_stats["valores_nulos"],
            "percentual_nulos": col_stats["percentual_nulos"],
            "valores_unicos": col_stats["valores_unicos"],
            "percentual_unicidade": col_stats["percentual_unicidade"],
            "is_pk_candidate": col_stats["is_pk_candidate"],
            "exemplos_gemini": col_stats["exemplos_gemini"],
            "amostra_fk": col_stats.get("amostra_fk"),
        }
        # Estatísticas numéricas opcionais
        for k in ("valor_min", "valor_max", "media"):
            if k in col_stats:
                entry[k] = col_stats[k]

        result.append(entry)
    return result
