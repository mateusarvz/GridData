import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.modules.catalog.infrastructure.orm_models import TenantBase, WorkspaceModel
from scripts.cleanup_cron import purge_expired_soft_deletes

@pytest_asyncio.fixture
async def setup_cleanup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    now = datetime.now(timezone.utc)
    
    async with session_maker() as session:
        # 1. Ativo (não deve ser deletado)
        ws_active = WorkspaceModel(
            id=uuid4(), name="Ativo", owner_id=uuid4(),
            is_deleted=False, deleted_at=None
        )
        # 2. Deletado há 5 dias (abaixo da retenção de 30 dias - não deve ser deletado)
        ws_recent = WorkspaceModel(
            id=uuid4(), name="Deletado Recente", owner_id=uuid4(),
            is_deleted=True, deleted_at=now - timedelta(days=5)
        )
        # 3. Deletado há 40 dias (acima da retenção de 30 dias - DEVE ser purgado!)
        ws_expired = WorkspaceModel(
            id=uuid4(), name="Deletado Antigo", owner_id=uuid4(),
            is_deleted=True, deleted_at=now - timedelta(days=40)
        )
        
        session.add_all([ws_active, ws_recent, ws_expired])
        await session.commit()
        
    yield (session_maker, [ws_active.id, ws_recent.id, ws_expired.id])
    await engine.dispose()

@pytest.mark.asyncio
async def test_purge_expired_soft_deletes_respects_retention_period(setup_cleanup_db):
    session_maker, (id_active, id_recent, id_expired) = setup_cleanup_db
    
    async with session_maker() as session:
        counts = await purge_expired_soft_deletes(session, [WorkspaceModel], retention_days=30)
        assert counts["workspaces"] == 1
        
        # Verificar no banco se apenas o expirado foi removido
        res_active = await session.execute(select(WorkspaceModel).where(WorkspaceModel.id == id_active))
        assert res_active.scalar_one_or_none() is not None
        
        res_recent = await session.execute(select(WorkspaceModel).where(WorkspaceModel.id == id_recent))
        assert res_recent.scalar_one_or_none() is not None
        
        res_expired = await session.execute(select(WorkspaceModel).where(WorkspaceModel.id == id_expired))
        assert res_expired.scalar_one_or_none() is None
