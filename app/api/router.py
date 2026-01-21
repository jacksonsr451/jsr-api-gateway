from fastapi import APIRouter

from app.api.routes import gateway, health, proxy

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(gateway.router, tags=["gateway"])
api_router.include_router(proxy.router, tags=["proxy"], include_in_schema=False)
