from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from app.modules.engine.domain.entities import DynamicRow

class IDynamicRowRepository(ABC):
    @abstractmethod
    async def get_by_id(self, row_id: UUID) -> Optional[DynamicRow]:
        pass

    @abstractmethod
    async def list_by_table(
        self,
        table_id: UUID,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> Tuple[List[DynamicRow], int]:
        """
        Retorna uma tupla contendo a lista de linhas paginadas e o total de registros que correspondem ao filtro.
        """
        pass

    @abstractmethod
    async def save(self, row: DynamicRow) -> DynamicRow:
        pass

    @abstractmethod
    async def delete(self, row_id: UUID) -> bool:
        pass
