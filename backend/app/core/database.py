from typing import Dict, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from app.core.config import settings

class TenantDatabaseManager:
    def __init__(self):
        # Engine e SessionMaker para o Banco Administrativo ("sistema")
        self.system_engine: AsyncEngine = create_async_engine(
            settings.DATABASE_SYSTEM_URL,
            echo=settings.ENVIRONMENT == "development",
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        self.system_session_maker = async_sessionmaker(
            bind=self.system_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Cache de Engines para Bancos de Clientes ("empresa_xxxx")
        self._tenant_engines: Dict[str, AsyncEngine] = {}
        self._tenant_session_makers: Dict[str, async_sessionmaker[AsyncSession]] = {}

    def get_tenant_engine(self, tenant_db_name: str, host: str = "localhost", port: int = 5432, user: str = "damabox_admin", password: str = "damabox_password_secret") -> AsyncEngine:
        if tenant_db_name not in self._tenant_engines:
            tenant_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{tenant_db_name}"
            engine = create_async_engine(
                tenant_url,
                echo=settings.ENVIRONMENT == "development",
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
            self._tenant_engines[tenant_db_name] = engine
            self._tenant_session_makers[tenant_db_name] = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._tenant_engines[tenant_db_name]

    def get_tenant_session_maker(self, tenant_db_name: str) -> async_sessionmaker[AsyncSession]:
        if tenant_db_name not in self._tenant_session_makers:
            self.get_tenant_engine(tenant_db_name)
        return self._tenant_session_makers[tenant_db_name]

    async def close_all_connections(self):
        await self.system_engine.dispose()
        for engine in self._tenant_engines.values():
            await engine.dispose()
        self._tenant_engines.clear()
        self._tenant_session_makers.clear()

db_manager = TenantDatabaseManager()

async def get_system_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.system_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
