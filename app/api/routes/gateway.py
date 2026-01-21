from fastapi import APIRouter, Depends, status

from app.api.deps import require_authorization
from app.core.config import get_settings
from app.schemas.routes import RouteConfig, RouteCreate, RouteUpdate
from app.services.routes_store import RouteStore, get_route_store

settings = get_settings()

router = APIRouter(
    dependencies=[Depends(require_authorization(settings.routes_admin_permission))]
)


@router.get("/routes", response_model=list[RouteConfig])
def list_routes(store: RouteStore = Depends(get_route_store)) -> list[RouteConfig]:
    return store.list_routes()


@router.get("/routes/{route_id}", response_model=RouteConfig)
def get_route(
    route_id: str, store: RouteStore = Depends(get_route_store)
) -> RouteConfig:
    return store.get_route(route_id)


@router.post(
    "/routes",
    response_model=RouteConfig,
    status_code=status.HTTP_201_CREATED,
)
def create_route(
    payload: RouteCreate, store: RouteStore = Depends(get_route_store)
) -> RouteConfig:
    return store.create_route(payload)


@router.put("/routes/{route_id}", response_model=RouteConfig)
def update_route(
    route_id: str, payload: RouteUpdate, store: RouteStore = Depends(get_route_store)
) -> RouteConfig:
    return store.update_route(route_id, payload)


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(route_id: str, store: RouteStore = Depends(get_route_store)) -> None:
    store.delete_route(route_id)
