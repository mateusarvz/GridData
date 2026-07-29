from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.supabase import get_supabase_status
from app.shared.exceptions import DamaBoxDomainException
from app.shared.error_handlers import (
    damabox_domain_exception_handler,
    http_exception_handler,
    validation_exception_handler
)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Configurar CORS para permitir requisições do frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registrar Handlers RFC 7807
    app.add_exception_handler(DamaBoxDomainException, damabox_domain_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Registrar Routers
    from app.modules.iam.presentation.routers.auth_router import router as auth_router
    from app.modules.iam.presentation.routers.supabase_login_router import router as supabase_login_router
    from app.modules.catalog.presentation.routers.catalog_router import router as catalog_router
    from app.modules.engine.presentation.routers.engine_router import router as engine_router
    from app.modules.audit.presentation.routers.audit_router import router as audit_router
    from app.modules.data_session.presentation.routers.data_session_router import router as data_session_router
    from app.modules.schema_analysis.presentation.routers.schema_analysis_router import router as schema_analysis_router
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(supabase_login_router, prefix=f"{settings.API_V1_STR}/supabase")
    app.include_router(catalog_router, prefix=f"{settings.API_V1_STR}/catalog")
    app.include_router(engine_router, prefix=f"{settings.API_V1_STR}/engine")
    app.include_router(audit_router, prefix=f"{settings.API_V1_STR}/audit")
    app.include_router(data_session_router, prefix=f"{settings.API_V1_STR}")
    app.include_router(schema_analysis_router, prefix=f"{settings.API_V1_STR}/schema-analysis")

    @app.get("/health", tags=["System"])
    async def health_check():
        return {"status": "ok", "project": settings.PROJECT_NAME}

    @app.get("/api/v1/test-error", tags=["System"])
    async def trigger_test_error():
        raise DamaBoxDomainException(
            detail="Este é um teste de erro formatado pelo RFC 7807.",
            title="Teste de Erro",
            status_code=400
        )

    @app.get("/api/v1/supabase/health", tags=["System"])
    async def supabase_health():
        return get_supabase_status()

    return app

app = create_app()
