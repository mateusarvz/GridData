import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.modules.engine.infrastructure.repositories import DynamicRowSQLAlchemyRepository
from app.modules.engine.domain.entities import DynamicRow
from app.modules.audit.infrastructure.orm_models import AuditLogModel
from app.modules.audit.infrastructure.repositories import AuditLogSQLAlchemyRepository
from app.modules.audit.application.dto import InlineEditDTO, RevertDTO
from app.modules.audit.application.use_cases import (
    InlineEditRowUseCase,
    GetRowHistoryUseCase,
    RevertRowUseCase
)

@pytest_asyncio.fixture
async def session_and_repos():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        row_repo = DynamicRowSQLAlchemyRepository(session)
        audit_repo = AuditLogSQLAlchemyRepository(session)
        
        table_id = uuid4()
        row = DynamicRow.create(table_id, {"nome": "Cliente A", "status": "Lead", "score": 10})
        saved_row = await row_repo.save(row)
        
        yield (session, row_repo, audit_repo, saved_row)
    await engine.dispose()

@pytest.mark.asyncio
async def test_inline_edit_and_time_travel_reversion(session_and_repos):
    _, row_repo, audit_repo, row = session_and_repos
    row_id = str(row.id)
    user_id = str(uuid4())
    
    # 1. Inline Edit (de Lead -> Negociação e score 10 -> 50)
    edit_uc = InlineEditRowUseCase(row_repo, audit_repo)
    edit_dto = InlineEditDTO(
        user_id=user_id,
        new_data={"nome": "Cliente A", "status": "Negociação", "score": 50}
    )
    res_row = await edit_uc.execute(row_id, edit_dto)
    assert res_row.version == 2
    assert res_row.data["status"] == "Negociação"
    
    # 2. Check History
    hist_uc = GetRowHistoryUseCase(audit_repo)
    history = await hist_uc.execute(row_id)
    assert len(history) == 1
    assert history[0].action == "update"
    assert history[0].version == 2
    assert history[0].diff["status"]["old"] == "Lead"
    assert history[0].diff["status"]["new"] == "Negociação"
    
    # 3. Time Travel Reversion (reverter a mudança que gerou a versão 2)
    revert_uc = RevertRowUseCase(row_repo, audit_repo)
    revert_dto = RevertDTO(user_id=user_id, target_version=2)
    reverted_row = await revert_uc.execute(row_id, revert_dto)
    
    # Ao reverter a versão 2, o status deve voltar para "Lead" e score 10!
    assert reverted_row.data["status"] == "Lead"
    assert reverted_row.data["score"] == 10
    assert reverted_row.version == 3  # Reversão gera uma nova versão!
    
    # Checar que o log de reversão foi criado
    history_after = await hist_uc.execute(row_id)
    assert len(history_after) == 2
    assert history_after[0].action == "revert"
