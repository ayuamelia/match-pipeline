from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.config import settings
from app.schemas import ErrorDetail, ErrorResponse

log = structlog.get_logger()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.api_rate_limit],
    storage_uri=settings.redis_url,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info(
        "api_starting",
        version=settings.app_version,
        environment=settings.environment,
        scoring_mode="llm" if settings.use_llm_scoring else "rule_based",
    )
    yield
    log.info("api_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    # Routes
    from app.api.v1.matches import router as matches_router
    from app.api.v1.system import router as system_router

    app.include_router(matches_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")

    # ── Custom exception handlers ──────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        field_parts = [str(loc) for loc in first.get("loc", [])[1:]]
        field = ".".join(field_parts) if field_parts else None

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=first.get("msg", "Request validation failed."),
                    field=field,
                    details={"errors": errors},
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        log.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred. Please try again.",
                )
            ).model_dump(),
        )

    return app


app = create_app()
