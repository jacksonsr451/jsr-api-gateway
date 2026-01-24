from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import (
    AuthContext,
    AuthServiceClient,
    AuthServiceError,
    get_auth_service_client,
)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def require_authentication(
    token: str = Depends(get_bearer_token),
    client: AuthServiceClient = Depends(get_auth_service_client),
) -> AuthContext:
    try:
        claims = await client.validate_token(token)
    except AuthServiceError as exc:
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else None
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers=headers,
        ) from exc
    return AuthContext(token=token, claims=claims)


def require_authorization(permission: str):
    async def dependency(
        context: AuthContext = Depends(require_authentication),
        client: AuthServiceClient = Depends(get_auth_service_client),
    ) -> AuthContext:
        try:
            await client.authorize(context.token, permission)
        except AuthServiceError as exc:
            headers = (
                {"WWW-Authenticate": "Bearer"}
                if exc.status_code == status.HTTP_401_UNAUTHORIZED
                else None
            )
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.detail,
                headers=headers,
            ) from exc
        return context

    return dependency
