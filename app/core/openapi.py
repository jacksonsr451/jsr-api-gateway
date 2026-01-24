from __future__ import annotations

from typing import Any

from fastapi import status

from app.core.responses import ErrorResponse, build_error_payload

OPENAPI_DESCRIPTION = "Centralized OpenAPI schema for the API gateway."

OPENAPI_TAGS = [
    {"name": "health", "description": "Health check endpoints."},
    {"name": "gateway", "description": "Gateway administration routes."},
    {"name": "proxy", "description": "Proxy forwarding routes."},
]


ResponseDocs = dict[int | str, dict[str, Any]]


def _error_response(description: str, code: str) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {"application/json": {"example": build_error_payload(code, code)}},
    }


_ERROR_RESPONSES: ResponseDocs = {
    status.HTTP_400_BAD_REQUEST: _error_response("Bad request", "bad_request"),
    status.HTTP_401_UNAUTHORIZED: _error_response(
        "Not authenticated", "not_authenticated"
    ),
    status.HTTP_403_FORBIDDEN: _error_response("Not authorized", "not_authorized"),
    status.HTTP_404_NOT_FOUND: _error_response("Not found", "not_found"),
    status.HTTP_409_CONFLICT: _error_response("Conflict", "conflict"),
    status.HTTP_422_UNPROCESSABLE_ENTITY: _error_response(
        "Validation error", "validation_error"
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: _error_response("Rate limited", "rate_limited"),
    status.HTTP_500_INTERNAL_SERVER_ERROR: _error_response(
        "Internal server error", "internal_server_error"
    ),
    status.HTTP_502_BAD_GATEWAY: _error_response("Bad gateway", "bad_gateway"),
    status.HTTP_503_SERVICE_UNAVAILABLE: _error_response(
        "Service unavailable", "service_unavailable"
    ),
    status.HTTP_504_GATEWAY_TIMEOUT: _error_response(
        "Gateway timeout", "gateway_timeout"
    ),
}


def responses_for(*status_codes: int) -> ResponseDocs:
    return {code: _ERROR_RESPONSES[code] for code in status_codes}


def merge_responses(*responses: ResponseDocs) -> ResponseDocs:
    merged: ResponseDocs = {}
    for response in responses:
        merged.update(response)
    return merged


COMMON_RESPONSES = responses_for(
    status.HTTP_429_TOO_MANY_REQUESTS,
    status.HTTP_500_INTERNAL_SERVER_ERROR,
)
AUTH_RESPONSES = responses_for(
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
)
SERVICE_RESPONSES = responses_for(
    status.HTTP_502_BAD_GATEWAY,
    status.HTTP_503_SERVICE_UNAVAILABLE,
    status.HTTP_504_GATEWAY_TIMEOUT,
)
VALIDATION_RESPONSES = responses_for(status.HTTP_422_UNPROCESSABLE_ENTITY)
CONFLICT_RESPONSES = responses_for(status.HTTP_409_CONFLICT)
NOT_FOUND_RESPONSES = responses_for(status.HTTP_404_NOT_FOUND)

HEALTH_RESPONSES = merge_responses(COMMON_RESPONSES)
GATEWAY_LIST_RESPONSES = merge_responses(
    AUTH_RESPONSES, SERVICE_RESPONSES, COMMON_RESPONSES
)
GATEWAY_DETAIL_RESPONSES = merge_responses(GATEWAY_LIST_RESPONSES, NOT_FOUND_RESPONSES)
GATEWAY_CREATE_RESPONSES = merge_responses(
    GATEWAY_LIST_RESPONSES, VALIDATION_RESPONSES, CONFLICT_RESPONSES
)
GATEWAY_UPDATE_RESPONSES = merge_responses(
    GATEWAY_DETAIL_RESPONSES, VALIDATION_RESPONSES, CONFLICT_RESPONSES
)
GATEWAY_DELETE_RESPONSES = merge_responses(GATEWAY_DETAIL_RESPONSES)
