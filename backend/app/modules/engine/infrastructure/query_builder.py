from typing import List, Dict, Any, Optional
from sqlalchemy import Select, func, asc, desc, String
from app.modules.engine.infrastructure.orm_models import DynamicRowModel
from app.modules.engine.domain.value_objects import FilterOperator

def _extract_field(field: str):
    """
    Extrai um campo da coluna JSON 'data'.
    Usamos func.json_extract para compatibilidade limpa entre SQLite e PostgreSQL (JSONB).
    """
    return func.json_extract(DynamicRowModel.data, f"$.{field}")

def build_dynamic_query(
    stmt: Select,
    filters: Optional[List[Dict[str, Any]]] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = False
) -> Select:
    """
    Aplica filtros relacionais de operador (eq, ne, gt, gte, lt, lte, like, contains)
    e ordenação sobre campos dentro do payload JSONB da linha.
    """
    if filters:
        for f in filters:
            field = f.get("field")
            op = f.get("op", "eq")
            val = f.get("value")
            
            if not field or val is None:
                continue

            extracted = _extract_field(field)

            if op == FilterOperator.EQ.value or op == "eq":
                stmt = stmt.where(extracted == val)
            elif op == FilterOperator.NE.value or op == "ne":
                stmt = stmt.where(extracted != val)
            elif op == FilterOperator.GT.value or op == "gt":
                stmt = stmt.where(extracted > val)
            elif op == FilterOperator.GTE.value or op == "gte":
                stmt = stmt.where(extracted >= val)
            elif op == FilterOperator.LT.value or op == "lt":
                stmt = stmt.where(extracted < val)
            elif op == FilterOperator.LTE.value or op == "lte":
                stmt = stmt.where(extracted <= val)
            elif op == FilterOperator.LIKE.value or op == "like":
                # Convert to string for like comparison
                stmt = stmt.where(func.cast(extracted, String).like(f"%{val}%")) # type: ignore
            elif op == FilterOperator.CONTAINS.value or op == "contains":
                stmt = stmt.where(func.cast(extracted, String).like(f"%{val}%")) # type: ignore
            elif op == FilterOperator.IN.value or op == "in":
                if isinstance(val, list):
                    stmt = stmt.where(extracted.in_(val))

    if sort_by:
        extracted_sort = _extract_field(sort_by)
        if sort_desc:
            stmt = stmt.order_by(desc(extracted_sort))
        else:
            stmt = stmt.order_by(asc(extracted_sort))
    else:
        stmt = stmt.order_by(desc(DynamicRowModel.created_at))

    return stmt
