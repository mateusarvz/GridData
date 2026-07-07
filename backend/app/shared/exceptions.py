from typing import Any, Dict, Optional

class DamaBoxDomainException(Exception):
    def __init__(
        self,
        detail: str,
        title: str = "Erro de Domínio",
        status_code: int = 400,
        error_type: str = "https://api.damabox.com/errors/domain-error",
        extra_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(detail)
        self.detail = detail
        self.title = title
        self.status_code = status_code
        self.error_type = error_type
        self.extra_data = extra_data or {}
