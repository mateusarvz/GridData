from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.engine.domain.repositories import IDynamicRowRepository
from app.modules.engine.domain.entities import DynamicRow
from app.modules.engine.infrastructure.orm_models import DynamicRowModel
from app.modules.engine.infrastructure.query_builder import build_dynamic_query

class DynamicRowSQLAlchemyRepository(IDynamicRowRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: DynamicRowModel) -> DynamicRow:
        row = DynamicRow(
            table_id=model.table_id,
            data=model.data,
            version=model.version,
            entity_id=model.id
        )
        row.created_at = model.created_at
        row.updated_at = model.updated_at
        row.is_deleted = model.is_deleted
        row.deleted_at = model.deleted_at
        return row

    async def get_by_id(self, row_id: UUID) -> Optional[DynamicRow]:
        stmt = select(DynamicRowModel).where(DynamicRowModel.id == row_id, DynamicRowModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_table(
        self,
        table_id: UUID,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ) -> Tuple[List[DynamicRow], int]:
        base_stmt = select(DynamicRowModel).where(
            DynamicRowModel.table_id == table_id,
            DynamicRowModel.is_deleted == False
        )
        
        # Aplicar query builder (filtros e ordenação)
        filtered_stmt = build_dynamic_query(base_stmt, filters=filters, sort_by=sort_by, sort_desc=sort_desc)
        
        # Obter contagem total com o filtro aplicado
        count_stmt = select(func.count()).select_from(filtered_stmt.subquery())
        count_res = await self.session.execute(count_stmt)
        total_count = count_res.scalar_one()
        
        # Aplicar paginação
        paginated_stmt = filtered_stmt.limit(limit).offset(offset)
        result = await self.session.execute(paginated_stmt)
        models = result.scalars().all()
        
        return [self._to_entity(m) for m in models], total_count

    async def save(self, row: DynamicRow) -> DynamicRow:
        stmt = select(DynamicRowModel).where(DynamicRowModel.id == row.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.data = row.data
            existing.version = row.version
            existing.updated_at = row.updated_at
            existing.is_deleted = row.is_deleted
            existing.deleted_at = row.deleted_at
            model = existing
        else:
            model = DynamicRowModel(
                id=row.id,
                table_id=row.table_id,
                data=row.data,
                version=row.version,
                created_at=row.created_at,
                updated_at=row.updated_at,
                is_deleted=row.is_deleted,
                deleted_at=row.deleted_at
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, row_id: UUID) -> bool:
        stmt = select(DynamicRowModel).where(DynamicRowModel.id == row_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if not existing:
            return False
        
        existing.is_deleted = True
        await self.session.commit()
        return True
