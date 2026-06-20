"""JWT authentication and role-based authorization."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from hmac import compare_digest
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from .config import settings

bearer = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    subject: str
    role: str


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": subject,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expiration_minutes),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def authenticate_bootstrap_user(username: str, password: str) -> Principal | None:
    if compare_digest(username, settings.bootstrap_admin_username) and compare_digest(
        password, settings.bootstrap_admin_password
    ):
        return Principal(subject=username, role="admin")
    return None


async def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    if not settings.enable_auth:
        return Principal(subject="auth-disabled", role="admin")
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "role"]},
        )
        return Principal(subject=payload["sub"], role=payload["role"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def require_roles(*roles: str) -> Callable:
    async def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return dependency


viewer = require_roles("viewer", "editor", "admin")
editor = require_roles("editor", "admin")
admin = require_roles("admin")
