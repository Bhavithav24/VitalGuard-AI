"""Environment-backed authentication and role-based authorization for the synthetic demo API.

Supports the legacy single demo account plus an optional multi-account JSON
configuration. Passwords may be supplied as PBKDF2-SHA256 hashes for stronger
production configuration; plaintext is retained only as a backwards-compatible
demo fallback.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
_bearer = HTTPBearer(auto_error=False)
ACCESS_TOKEN_TTL_SECONDS = 900
_REVOKED_TOKENS: dict[str, float] = {}
Role = Literal["admin", "operator", "viewer"]
_VALID_ROLES = {"admin", "operator", "viewer"}


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role


def _password_hash_matches(password: str, encoded: str) -> bool:
    try:
        scheme, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        iterations = int(iterations_text)
        if scheme != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        padding = lambda value: value + "=" * (-len(value) % 4)
        salt = base64.urlsafe_b64decode(padding(salt_text))
        expected = base64.urlsafe_b64decode(padding(digest_text))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _credentials() -> tuple[str, str, str, str, Role]:
    username = os.getenv("VITALGUARD_AUTH_USERNAME", "").strip()
    password = os.getenv("VITALGUARD_AUTH_PASSWORD", "")
    password_hash = os.getenv("VITALGUARD_AUTH_PASSWORD_HASH", "").strip()
    secret = os.getenv("VITALGUARD_AUTH_SECRET", "")
    role = os.getenv("VITALGUARD_AUTH_ROLE", "admin").strip().lower()
    if role not in _VALID_ROLES:
        raise HTTPException(status_code=503, detail="Authentication role is invalid")
    if not secret or len(secret) < 32:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    if not os.getenv("VITALGUARD_AUTH_USERS_JSON", "").strip() and (not username or (not password and not password_hash)):
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    return username, password, password_hash, secret, role  # type: ignore[return-value]


def _accounts() -> list[dict[str, str]]:
    raw = os.getenv("VITALGUARD_AUTH_USERS_JSON", "").strip()
    if raw:
        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=503, detail="Authentication users are not configured correctly") from exc
        if not isinstance(records, list) or not records or len(records) > 100:
            raise HTTPException(status_code=503, detail="Authentication users are not configured correctly")
        accounts = []
        for record in records:
            if not isinstance(record, dict):
                raise HTTPException(status_code=503, detail="Authentication users are not configured correctly")
            username = str(record.get("username", "")).strip()
            password_hash = str(record.get("password_hash", "")).strip()
            role = str(record.get("role", "")).strip().lower()
            if not username or len(username) > 128 or not password_hash or role not in _VALID_ROLES:
                raise HTTPException(status_code=503, detail="Authentication users are not configured correctly")
            accounts.append({"username": username, "password": "", "password_hash": password_hash, "role": role})
        return accounts
    username, password, password_hash, _, role = _credentials()
    return [{"username": username, "password": password, "password_hash": password_hash, "role": role}]


def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=secret, salt="vitalguard-access-v2")


def _verify_password(password: str, account: dict[str, str]) -> bool:
    if account["password_hash"]:
        return _password_hash_matches(password, account["password_hash"])
    return hmac.compare_digest(password, account["password"])


def validate_access_token(token: str | None) -> dict[str, str]:
    _, _, _, secret, _ = _credentials()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = _serializer(secret).loads(token, max_age=ACCESS_TOKEN_TTL_SECONDS)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Access token expired", headers={"WWW-Authenticate": "Bearer"})
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid access token", headers={"WWW-Authenticate": "Bearer"})
    if not isinstance(payload, dict) or payload.get("type") != "access" or not isinstance(payload.get("sub"), str):
        raise HTTPException(status_code=401, detail="Invalid access token", headers={"WWW-Authenticate": "Bearer"})
    account = next((item for item in _accounts() if hmac.compare_digest(item["username"], payload["sub"])), None)
    if account is None or payload.get("role") != account["role"]:
        raise HTTPException(status_code=401, detail="Account or role is no longer valid", headers={"WWW-Authenticate": "Bearer"})
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti or jti in _REVOKED_TOKENS:
        raise HTTPException(status_code=401, detail="Access token revoked", headers={"WWW-Authenticate": "Bearer"})
    return {"sub": account["username"], "role": account["role"], "jti": jti}


def authenticate_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    return validate_access_token(credentials.credentials)


def require_roles(*allowed_roles: Role):
    if not allowed_roles:
        raise ValueError("At least one allowed role is required")

    def dependency(principal: Annotated[dict[str, str], Depends(authenticate_principal)]) -> dict[str, str]:
        if principal.get("role") not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
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
    _login_attempts[client_key] = recent


@router.post("/login", response_model=TokenResponse)
def login(request: Request, payload: LoginRequest) -> TokenResponse:
    _, _, _, secret, _ = _credentials()
    client_host = request.client.host if request.client else "unknown"
    client_key = f"{client_host}:{payload.username.lower()}"
    _check_login_rate_limit(client_key)
    account = next((item for item in _accounts() if hmac.compare_digest(payload.username, item["username"])), None)
    if account is None or not _verify_password(payload.password, account):
        recent = _login_attempts.get(client_key, [])
        recent.append(time.monotonic())
        _login_attempts[client_key] = recent[-_LOGIN_MAX_ATTEMPTS:]
        raise HTTPException(status_code=401, detail="Invalid username or password", headers={"WWW-Authenticate": "Bearer"})
    _login_attempts.pop(client_key, None)
    token = _serializer(secret).dumps({"sub": account["username"], "type": "access", "role": account["role"], "jti": secrets.token_urlsafe(18)})
    return TokenResponse(access_token=token, expires_in=ACCESS_TOKEN_TTL_SECONDS, role=account["role"])


@router.get("/me")
def current_identity(principal: Annotated[dict[str, str], Depends(authenticate_principal)]):
    return {"subject": principal["sub"], "role": principal["role"], "authenticated": True}


@router.post("/logout", status_code=204)
def logout(principal: Annotated[dict[str, str], Depends(authenticate_principal)]):
    _REVOKED_TOKENS[principal["jti"]] = time.time() + ACCESS_TOKEN_TTL_SECONDS
    cutoff = time.time()
    for token_id, expires_at in list(_REVOKED_TOKENS.items()):
        if expires_at <= cutoff:
            _REVOKED_TOKENS.pop(token_id, None)
    return None


@router.get("/roles")
def role_permissions(principal: Annotated[dict[str, str], Depends(authenticate_principal)]):
    return {
        "current_role": principal["role"],
        "roles": {
            "admin": ["read", "predict", "ingest", "manage_alerts", "operations"],
            "operator": ["read", "predict", "ingest", "manage_alerts"],
            "viewer": ["read", "explain"],
        },
        "demo_only": True,
    }
