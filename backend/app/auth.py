"""Environment-backed authentication and role authorization for the synthetic demo API.

This module is intentionally small and explicit. It supports the current demo
operator plus a role claim so API permissions are enforced consistently.
For real clinical production, replace this bootstrap with a managed identity
provider and centrally managed user/role lifecycle.
"""
import hmac
import os
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
_bearer = HTTPBearer(auto_error=False)
ACCESS_TOKEN_TTL_SECONDS = 900
Role = Literal["admin", "operator", "viewer"]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role


def _credentials() -> tuple[str, str, str, Role]:
    username = os.getenv("VITALGUARD_AUTH_USERNAME", "").strip()
    password = os.getenv("VITALGUARD_AUTH_PASSWORD", "")
    secret = os.getenv("VITALGUARD_AUTH_SECRET", "")
    role = os.getenv("VITALGUARD_AUTH_ROLE", "operator").strip().lower()
    if role not in {"admin", "operator", "viewer"}:
        raise HTTPException(status_code=503, detail="Authentication role is invalid")
    if not username or not password or len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    return username, password, secret, role  # type: ignore[return-value]


def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=secret, salt="vitalguard-access-v2")


def validate_access_token(token: str | None) -> dict[str, str]:
    """Validate a bearer token supplied by HTTP or a WebSocket handshake."""
    _, _, secret, configured_role = _credentials()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = _serializer(secret).loads(token, max_age=ACCESS_TOKEN_TTL_SECONDS)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Access token expired",
                            headers={"WWW-Authenticate": "Bearer"})
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid access token",
                            headers={"WWW-Authenticate": "Bearer"})
    if not isinstance(payload, dict) or payload.get("type") != "access" or not isinstance(payload.get("sub"), str):
        raise HTTPException(status_code=401, detail="Invalid access token",
                            headers={"WWW-Authenticate": "Bearer"})
    configured_username, _, _, _ = _credentials()
    if not hmac.compare_digest(payload["sub"], configured_username):
        raise HTTPException(status_code=401, detail="Account is no longer valid",
                            headers={"WWW-Authenticate": "Bearer"})
    token_role = payload.get("role")
    if token_role != configured_role:
        raise HTTPException(status_code=401, detail="Account role is no longer valid",
                            headers={"WWW-Authenticate": "Bearer"})
    return {"sub": payload["sub"], "role": configured_role}


def authenticate_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, str]:
    """Validate an access token and return its authenticated subject and role."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})
    return validate_access_token(credentials.credentials)


def require_roles(*allowed_roles: Role):
    """Return a FastAPI dependency that enforces explicit role authorization."""
    if not allowed_roles:
        raise ValueError("At least one allowed role is required")

    def dependency(principal: Annotated[dict[str, str], Depends(authenticate_principal)]) -> dict[str, str]:
        if principal.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return dependency


_LOGIN_WINDOW_SECONDS = 60
_LOGIN_MAX_ATTEMPTS = 10
_login_attempts: dict[str, list[float]] = {}


def _check_login_rate_limit(client_key: str) -> None:
    now = time.monotonic()
    recent = [stamp for stamp in _login_attempts.get(client_key, []) if now - stamp < _LOGIN_WINDOW_SECONDS]
    if len(recent) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts; try again shortly")
    recent.append(now)
    _login_attempts[client_key] = recent


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """Issue a short-lived bearer token for the configured demo operator."""
    username, password, secret, role = _credentials()
    _check_login_rate_limit(payload.username.lower())
    if not hmac.compare_digest(payload.username, username) or not hmac.compare_digest(payload.password, password):
        raise HTTPException(status_code=401, detail="Invalid username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    token = _serializer(secret).dumps({"sub": username, "type": "access", "role": role})
    return TokenResponse(access_token=token, expires_in=ACCESS_TOKEN_TTL_SECONDS, role=role)


@router.get("/me")
def current_identity(principal: Annotated[dict[str, str], Depends(authenticate_principal)]):
    return {"subject": principal["sub"], "role": principal["role"], "authenticated": True}
