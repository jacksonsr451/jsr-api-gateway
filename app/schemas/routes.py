from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, PrivateAttr, field_validator


class RouteRewrite(BaseModel):
    regex_uri: tuple[str, str] | None = None
    uri: str | None = None


class RouteAuth(BaseModel):
    required: bool = False
    permission: str | None = None
    roles: list[str] = Field(default_factory=list)


class RouteConfig(BaseModel):
    id: str
    name: str
    regex: str
    upstream_base_url: str
    methods: list[str] = Field(default_factory=list)
    rewrite: RouteRewrite | None = None
    auth: RouteAuth | None = None
    priority: int = 0
    enabled: bool = True
    timeout_seconds: float | None = None

    _compiled_regex: re.Pattern[str] | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        self._compiled_regex = re.compile(self.regex)

    @field_validator("methods", mode="before")
    @classmethod
    def normalize_methods(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw = [item.strip() for item in value.split(",")]
            return [item.upper() for item in raw if item]
        return [str(item).upper() for item in value if str(item).strip()]

    @field_validator("upstream_base_url")
    @classmethod
    def validate_upstream_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("upstream_base_url must be a valid http(s) URL")
        return value.rstrip("/")

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return value

    def matches(self, method: str, path: str) -> bool:
        if not self.enabled:
            return False
        method_upper = method.upper()
        if self.methods:
            if method_upper not in self.methods and not (
                method_upper == "HEAD" and "GET" in self.methods
            ):
                return False
        if not self._compiled_regex:
            self._compiled_regex = re.compile(self.regex)
        return bool(self._compiled_regex.search(path))

    def rewrite_path(self, path: str) -> str:
        if not self.rewrite:
            return path
        if self.rewrite.regex_uri:
            pattern, replacement = self.rewrite.regex_uri
            return re.sub(pattern, replacement, path)
        if self.rewrite.uri:
            return self.rewrite.uri
        return path


class RouteCreate(BaseModel):
    id: str | None = None
    name: str
    regex: str
    upstream_base_url: str
    methods: list[str] = Field(default_factory=list)
    rewrite: RouteRewrite | None = None
    auth: RouteAuth | None = None
    priority: int = 0
    enabled: bool = True
    timeout_seconds: float | None = None


class RouteUpdate(BaseModel):
    name: str | None = None
    regex: str | None = None
    upstream_base_url: str | None = None
    methods: list[str] | None = None
    rewrite: RouteRewrite | None = None
    auth: RouteAuth | None = None
    priority: int | None = None
    enabled: bool | None = None
    timeout_seconds: float | None = None
