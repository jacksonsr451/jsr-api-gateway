from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimitMiddleware, RateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        allow_credentials=settings.cors_allow_credentials,
    )

    rate_limit_enabled = (
        settings.rate_limit_enabled
        and settings.rate_limit_requests > 0
        and settings.rate_limit_window_seconds > 0
    )
    app.add_middleware(
        RateLimitMiddleware,
        limiter=RateLimiter(
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        ),
        enabled=rate_limit_enabled,
        exempt_paths=settings.rate_limit_exempt_paths,
        key_header=settings.rate_limit_key_header,
    )

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
