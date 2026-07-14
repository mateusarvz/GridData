"""
Mascaramento de colunas e valores sensíveis.
Aplicado antes de qualquer payload enviado ao Gemini.
"""
import re
from typing import Any

# Padrão de nomes de coluna sensíveis
_SENSITIVE_COL = re.compile(
    r"(cpf|cnpj|rg|senha|password|secret|token|credit_card|cartao|telefone|"
    r"phone|celular|email|e_mail|ssn|cep|endereco|address|nascimento|birth|"
    r"pis|pasep|nit|numero_cartao|pan|cvv)",
    re.IGNORECASE,
)

# Padrões de valores sensíveis
_CPF_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")  # Exige separadores: 000.000.000-00
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_CARD_RE = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")

_PLACEHOLDER = "[valor mascarado - possível dado sensível]"


def is_sensitive_col(col_name: str) -> bool:
    """True se o nome da coluna sugere dado pessoal/sensível."""
    return bool(_SENSITIVE_COL.search(col_name))


def is_sensitive_value(value: str) -> bool:
    """True se o valor bruto bate em algum padrão sensível."""
    s = str(value)
    return bool(_CPF_RE.search(s) or _EMAIL_RE.search(s) or _CARD_RE.search(s))


def mask_samples(col_name: str, values: list[Any], *, max_values: int = 8) -> list[str]:
    """
    Mascara lista de amostras para envio ao Gemini.

    - Se a coluna é sensível por nome: retorna placeholder único.
    - Se algum valor bate em padrão sensível: substitui individualmente.
    - Nunca inclui dados reais de colunas sensíveis.
    """
    if is_sensitive_col(col_name):
        return [_PLACEHOLDER]

    result: list[str] = []
    for v in values[:max_values]:
        s = str(v)
        result.append(_PLACEHOLDER if is_sensitive_value(s) else s)
    return result
