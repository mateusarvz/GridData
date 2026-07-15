from datetime import datetime, timezone
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from app.shared.exceptions import DamaBoxDomainException

async def damabox_domain_exception_handler(request: Request, exc: DamaBoxDomainException) -> JSONResponse:
    problem_details = {
        "type": exc.error_type,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": str(request.url.path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **exc.extra_data
    }
    return JSONResponse(status_code=exc.status_code, content=problem_details)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    problem_details = {
        "type": "https://api.damabox.com/errors/http-error",
        "title": "Erro HTTP",
        "status": exc.status_code,
        "detail": str(exc.detail),
        "instance": str(request.url.path),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return JSONResponse(status_code=exc.status_code, content=problem_details)

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    problem_details = {
        "type": "https://api.damabox.com/errors/validation-error",
        "title": "Erro de Validação",
        "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "detail": "Um ou mais campos contêm valores incorretos ou ausentes.",
        "instance": str(request.url.path),
        "invalid_params": exc.errors(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=problem_details)
