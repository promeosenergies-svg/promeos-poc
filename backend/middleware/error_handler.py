"""
PROMEOS — Global error handler middleware.
Catches HTTPException and Pydantic ValidationError, returns standard APIError JSON.
"""

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.error import APIError

logger = logging.getLogger("promeos.errors")


def register_error_handlers(app: FastAPI):
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        correlation_id = str(uuid.uuid4())[:8]

        # Map common status codes to error codes
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
        }
        error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")

        error = APIError(
            code=error_code,
            message=str(exc.detail),
            correlation_id=correlation_id,
        )

        logger.warning(
            "HTTP %d [%s] %s %s — %s",
            exc.status_code,
            correlation_id,
            request.method,
            request.url.path,
            exc.detail,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = str(uuid.uuid4())[:8]

        # Build a readable message from Pydantic errors
        errors = exc.errors()
        details = []
        for err in errors:
            loc = " → ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "")
            details.append(f"{loc}: {msg}")

        error = APIError(
            code="VALIDATION_ERROR",
            message="Erreur de validation des donnees",
            hint="; ".join(details) if details else None,
            correlation_id=correlation_id,
        )

        logger.info(
            "Validation error [%s] %s %s — %d errors",
            correlation_id,
            request.method,
            request.url.path,
            len(errors),
        )

        return JSONResponse(
            status_code=422,
            content=error.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        correlation_id = str(uuid.uuid4())[:8]

        error = APIError(
            code="INTERNAL_ERROR",
            message="Erreur interne du serveur",
            hint="Contactez le support avec le correlation_id",
            correlation_id=correlation_id,
        )

        logger.error(
            "Unhandled exception [%s] %s %s — %s: %s",
            correlation_id,
            request.method,
            request.url.path,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content=error.model_dump(),
        )
