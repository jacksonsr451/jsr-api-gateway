from __future__ import annotations

import uuid
from pathlib import Path
from threading import RLock
from typing import Iterable

import yaml
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.routes import RouteConfig, RouteCreate, RouteUpdate


class RouteStore:
    def __init__(self, file_path: str) -> None:
        self._path = Path(file_path)
        self._lock = RLock()
        self._cache: list[RouteConfig] = []
        self._mtime: float | None = None

    def list_routes(self) -> list[RouteConfig]:
        return list(self._load())

    def get_route(self, route_id: str) -> RouteConfig:
        for route in self._load():
            if route.id == route_id:
                return route
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="route_not_found"
        )

    def create_route(self, payload: RouteCreate) -> RouteConfig:
        with self._lock:
            routes = self._load()
            route_id = payload.id or uuid.uuid4().hex
            if any(route.id == route_id for route in routes):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="route_id_exists"
                )
            if any(route.name == payload.name for route in routes):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="route_name_exists"
                )

            route = RouteConfig(
                id=route_id, **payload.model_dump(exclude={"id"}, exclude_none=True)
            )
            routes.append(route)
            self._save(routes)
            return route

    def update_route(self, route_id: str, payload: RouteUpdate) -> RouteConfig:
        with self._lock:
            routes = self._load()
            for index, existing in enumerate(routes):
                if existing.id != route_id:
                    continue
                data = existing.model_dump()
                updates = payload.model_dump(exclude_unset=True)
                if "name" in updates and any(
                    route.name == updates["name"] and route.id != route_id
                    for route in routes
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="route_name_exists",
                    )
                data.update(updates)
                data["id"] = route_id
                updated = RouteConfig(**data)
                routes[index] = updated
                self._save(routes)
                return updated
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="route_not_found"
            )

    def delete_route(self, route_id: str) -> None:
        with self._lock:
            routes = self._load()
            remaining = [route for route in routes if route.id != route_id]
            if len(remaining) == len(routes):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="route_not_found"
                )
            self._save(remaining)

    def match_route(self, method: str, path: str) -> RouteConfig | None:
        candidates = [
            route for route in self._load() if route.matches(method=method, path=path)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda route: route.priority, reverse=True)
        return candidates[0]

    def _load(self) -> list[RouteConfig]:
        with self._lock:
            if not self._path.exists():
                self._cache = []
                self._mtime = None
                return []
            stat = self._path.stat()
            if self._mtime is not None and stat.st_mtime == self._mtime:
                return list(self._cache)
            data = yaml.safe_load(self._path.read_text()) or {}
            raw_routes = _extract_routes(data)
            routes = [RouteConfig(**payload) for payload in raw_routes]
            self._cache = routes
            self._mtime = stat.st_mtime
            return list(routes)

    def _save(self, routes: Iterable[RouteConfig]) -> None:
        payload = {
            "routes": [
                route.model_dump(mode="json", exclude_none=True) for route in routes
            ]
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        tmp_path.write_text(yaml.safe_dump(payload, sort_keys=False))
        tmp_path.replace(self._path)
        self._cache = list(routes)
        self._mtime = self._path.stat().st_mtime


def get_route_store() -> RouteStore:
    settings = get_settings()
    return RouteStore(settings.routes_config_path)


def _extract_routes(data: object) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        raw = data.get("routes")
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
    return []
