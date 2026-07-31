"""
Cálculo de estatísticas descritivas por coluna a partir de um DataFrame pandas.

Chamado no momento do upload (CriarSessaoUseCase) — os resultados são
gravados no JSONB colunas_schema em schema_analysis_tables e usados depois
pelo InferirSchemaUseCase para enriquecer o payload do Gemini e calcular
candidatos a FK sem precisar re-ler os arquivos originais.
"""
import random
import re
import uuid
from decimal import Decimal
from typing import Any

import pandas as pd

from app.services.data_masking_service import is_sensitive_col, mask_samples

# Limite de amostras únicas armazenadas para detecção de overlap (backend only)
_MAX_AMOSTRA_FK = 200
# Limite de exemplos enviados ao Gemini
_MAX_EXEMPLOS_GEMINI = 8
# Limite mínimo de linhas lidas na análise de schema
_MAX_ANALYSIS_ROWS = 50

_DATE_REGEXES = (
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    re.compile(r"^\d{2}/\d{2}/\d{4}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$"),
)

_INTEGER_REGEX = re.compile(r"^[+-]?\d+$")
_DECIMAL_REGEX = re.compile(r"^[+-]?\d+[.,]\d+$")
_UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)

_BOOLEAN_VALUES = {"true", "false", "yes", "no", "1", "0", "sim", "nao", "não"}


def _normalize_sample_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value).strip()


def _parse_datetime_value(value: str) -> pd.Timestamp | None:
    if not value:
        return None
    try:
        if re.match(r"^\d{2}/\d{2}/\d{4}$", value):
            return pd.to_datetime(value, format="%d/%m/%Y", errors="coerce")
        if re.match(r"^\d{4}/\d{2}/\d{2}$", value):
            return pd.to_datetime(value, format="%Y/%m/%d", errors="coerce")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return pd.to_datetime(value, format="%Y-%m-%d", errors="coerce")
        if re.match(r"^\d{2}/\d{2}/\d{4}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?$", value):
            return pd.to_datetime(value, format="%d/%m/%Y %H:%M:%S", errors="coerce")
        if re.match(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$", value):
            return pd.to_datetime(value, errors="coerce", utc=False)
    except Exception:
        return None
    return None


def _looks_like_date(values: list[Any]) -> bool:
    checked = 0
    matches = 0
    for raw in values:
        value = _normalize_sample_value(raw)
        if not value:
            continue
        checked += 1
        if any(regex.match(value) for regex in _DATE_REGEXES):
            matches += 1
            continue
        if _parse_datetime_value(value) is not None:
            matches += 1
    return checked > 0 and matches / checked >= 0.8


def _looks_like_timestamp(values: list[Any]) -> bool:
    checked = 0
    matches = 0
    for raw in values:
        value = _normalize_sample_value(raw)
        if not value:
            continue
        checked += 1
        parsed = _parse_datetime_value(value)
        if parsed is not None and (" " in value or "T" in value):
            matches += 1
    return checked > 0 and matches / checked >= 0.8


def _looks_like_uuid(values: list[Any]) -> bool:
    checked = 0
    matches = 0
    for raw in values:
        value = _normalize_sample_value(raw)
        if not value:
            continue
        checked += 1
        if _UUID_REGEX.match(value):
            matches += 1
    return checked > 0 and matches / checked >= 0.9


def _looks_like_integer(values: list[Any]) -> bool:
    checked = 0
    matches = 0
    for raw in values:
        value = _normalize_sample_value(raw)
        if not value:
            continue
        checked += 1
        if _INTEGER_REGEX.match(value):
            matches += 1
    return checked > 0 and matches / checked >= 0.9


def _looks_like_decimal(values: list[Any]) -> bool:
    checked = 0
    matches = 0
    for raw in values:
        value = _normalize_sample_value(raw).replace(" ", "")
        if not value:
            continue
        checked += 1
        if _DECIMAL_REGEX.match(value):
            matches += 1
            continue
        try:
            Decimal(value.replace(",", "."))
            if "." in value or "," in value:
                matches += 1
        except Exception:
            continue
    return checked > 0 and matches / checked >= 0.9


def _looks_like_boolean(values: list[Any]) -> bool:
    checked = 0
    matches = 0
    for raw in values:
        value = _normalize_sample_value(raw).lower()
        if not value:
            continue
        checked += 1
        if value in _BOOLEAN_VALUES:
            matches += 1
    return checked > 0 and matches / checked >= 0.95


def infer_postgres_type(series: pd.Series) -> str:
    """
    Heurística local de tipo.
    Ordem: DATE, BOOLEAN, INT, BIGINT, DECIMAL/NUMERIC, VARCHAR, TEXT.
    """
    non_null = series.dropna()
    if len(non_null) == 0:
        return "TEXT"

    values = non_null.tolist()

    if _looks_like_uuid(values):
        return "UUID"
    if pd.api.types.is_datetime64_any_dtype(series) or _looks_like_timestamp(values):
        return "TIMESTAMP WITH TIME ZONE"
    if _looks_like_date(values):
        return "DATE"
    if pd.api.types.is_bool_dtype(series) or _looks_like_boolean(values):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series) or _looks_like_integer(values):
        try:
            max_abs = max(abs(int(v)) for v in non_null.tolist())
            if max_abs <= 2147483647:
                return "INT"
            if max_abs <= 9223372036854775807:
                return "BIGINT"
        except Exception:
            return "BIGINT"
        return "BIGINT"
    if pd.api.types.is_float_dtype(series) or _looks_like_decimal(values):
        return "DECIMAL(18,6)"

    unique_ratio = non_null.nunique(dropna=True) / len(non_null) if len(non_null) else 0.0
    if unique_ratio >= 0.5 and len(non_null) <= 500:
        return "VARCHAR(255)"

    return "TEXT"


def normalize_for_postgres(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, Decimal)):
        return value
    if isinstance(value, float):
        if float(value).is_integer():
            return int(value)
        return value
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            return value.isoformat()
        return value.isoformat(sep=" ")

    text = str(value).strip()
    if not text:
        return None
    if _UUID_REGEX.match(text):
        return str(uuid.UUID(text))
    if any(regex.match(text) for regex in _DATE_REGEXES):
        parsed = _parse_datetime_value(text)
        if not pd.isna(parsed):
            return parsed.isoformat(sep=" ")
    if _INTEGER_REGEX.match(text):
        try:
            return int(text)
        except Exception:
            return text
    if _DECIMAL_REGEX.match(text):
        normalized = text.replace(" ", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except Exception:
            return normalized
    try:
        parsed_decimal = Decimal(text.replace(",", "."))
        if "." in text or "," in text:
            return parsed_decimal
    except Exception:
        pass
    return value


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
        "tipo_sugerido": infer_postgres_type(series),
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
            "tipo_sugerido": col_stats["tipo_sugerido"],
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


def sample_dataframe_for_analysis(df: pd.DataFrame, max_rows: int = _MAX_ANALYSIS_ROWS) -> pd.DataFrame:
    """
    Reduz dataframe para análise de schema.
    Usa só amostra; não lê dataset inteiro outra vez.
    """
    if len(df) <= max_rows:
        return df
    return df.head(max_rows)
