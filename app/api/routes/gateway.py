from anyio import to_thread
from fastapi import APIRouter, Depends, status

from app.api.deps import require_authorization
from app.core.config import get_settings
from app.core.openapi import (
    GATEWAY_CREATE_RESPONSES,
    GATEWAY_DELETE_RESPONSES,
    GATEWAY_DETAIL_RESPONSES,
    GATEWAY_LIST_RESPONSES,
    GATEWAY_UPDATE_RESPONSES,
)
from app.core.responses import DataResponse, build_data_payload
from app.schemas.routes import RouteConfig, RouteCreate, RouteUpdate
from app.services.routes_store import RouteStore, get_route_store

settings = get_settings()

router = APIRouter(
    dependencies=[Depends(require_authorization(settings.routes_admin_permission))]
)


@router.get(
    "/routes",
    response_model=DataResponse[list[RouteConfig]],
    responses=GATEWAY_LIST_RESPONSES,
    summary="List routes",
)
async def list_routes(
    store: RouteStore = Depends(get_route_store),
) -> dict[str, list[RouteConfig]]:
    routes = await to_thread.run_sync(store.list_routes)
    return build_data_payload(routes)


@router.get(
    "/routes/{route_id}",
    response_model=DataResponse[RouteConfig],
    responses=GATEWAY_DETAIL_RESPONSES,
    summary="Get route",
)
async def get_route(
    route_id: str, store: RouteStore = Depends(get_route_store)
) -> dict[str, RouteConfig]:
    route = await to_thread.run_sync(store.get_route, route_id)
    return build_data_payload(route)


@router.post(
    "/routes",
    response_model=DataResponse[RouteConfig],
    responses=GATEWAY_CREATE_RESPONSES,
    status_code=status.HTTP_201_CREATED,
    summary="Create route",
)
async def create_route(
    payload: RouteCreate, store: RouteStore = Depends(get_route_store)
) -> dict[str, RouteConfig]:
    route = await to_thread.run_sync(store.create_route, payload)
    return build_data_payload(route)


@router.put(
    "/routes/{route_id}",
    response_model=DataResponse[RouteConfig],
    responses=GATEWAY_UPDATE_RESPONSES,
    summary="Update route",
)
async def update_route(
    route_id: str, payload: RouteUpdate, store: RouteStore = Depends(get_route_store)
) -> dict[str, RouteConfig]:
    route = await to_thread.run_sync(store.update_route, route_id, payload)
    return build_data_payload(route)


@router.delete(
    "/routes/{route_id}",
    response_model=DataResponse[dict[str, bool]],
    responses=GATEWAY_DELETE_RESPONSES,
    summary="Delete route",
)
async def delete_route(
    route_id: str, store: RouteStore = Depends(get_route_store)
) -> dict[str, dict[str, bool]]:
    await to_thread.run_sync(store.delete_route, route_id)
    return build_data_payload({"deleted": True})
