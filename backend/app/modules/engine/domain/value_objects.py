import json
from enum import Enum
from typing import Dict, Any
from app.shared.exceptions import DamaBoxDomainException

class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    IN = "in"
    CONTAINS = "contains"

class RowData:
    def __init__(self, value: Dict[str, Any]):
        if not isinstance(value, dict):
            raise DamaBoxDomainException("O payload da linha deve ser um dicionário.", status_code=400)
        try:
            # Validar que é serializável em JSON
            json.dumps(value)
        except (TypeError, ValueError) as e:
            raise DamaBoxDomainException(f"O valor informado não é serializável em JSON: {str(e)}", status_code=400)
        
        self._value = value

    @property
    def value(self) -> Dict[str, Any]:
        return self._value
