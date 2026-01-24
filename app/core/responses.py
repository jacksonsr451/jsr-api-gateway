from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class DataResponse(BaseModel, Generic[T]):
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def build_data_payload(data: Any) -> dict[str, Any]:
    return {"data": data}


def build_error_payload(
    code: str, message: str | None = None, details: Any | None = None
) -> dict[str, Any]:
    payload = {"error": {"code": code, "message": message or code}}
    if details is not None:
        payload["error"]["details"] = details
    return payload
