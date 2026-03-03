from dataclasses import dataclass
from functools import lru_cache

from fastapi import HTTPException, status
from jose import JWTError, jwt
import requests

from app.core.config import get_settings


@dataclass
class TokenData:
    sub: str
    preferred_username: str
    email: str | None
    roles: set[str]
    tenant_name: str | None


def _normalize_public_key(raw_key: str) -> str:
    if not raw_key:
        return ""
    if "BEGIN PUBLIC KEY" in raw_key:
        return raw_key
    return "-----BEGIN PUBLIC KEY-----\n" + raw_key + "\n-----END PUBLIC KEY-----"


@lru_cache(maxsize=1)
def _fetch_keycloak_certs(issuer: str) -> dict:
    certs_url = f"{issuer.rstrip('/')}/protocol/openid-connect/certs"
    try:
        response = requests.get(certs_url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch Keycloak signing certificates.",
        ) from exc
    return response.json()


def _resolve_signing_key(token: str, public_key: str, issuer: str) -> str:
    if public_key:
        return public_key

    if not issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Set KEYCLOAK_PUBLIC_KEY or KEYCLOAK_ISSUER for JWT validation.",
        )

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token header.") from exc

    kid = header.get("kid")
    certs = _fetch_keycloak_certs(issuer)
    for key in certs.get("keys", []):
        if key.get("kid") == kid and key.get("x5c"):
            cert = key["x5c"][0]
            return f"-----BEGIN CERTIFICATE-----\n{cert}\n-----END CERTIFICATE-----"

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unable to resolve signing key for token.")


def decode_and_validate_token(token: str) -> TokenData:
    """Validate Keycloak JWT and extract claims used by the API."""

    settings = get_settings()
    public_key = _normalize_public_key(settings.keycloak_public_key)
    signing_key = _resolve_signing_key(token, public_key, settings.keycloak_issuer)

    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer or None,
            options={"verify_aud": bool(settings.keycloak_audience)},
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication token.") from exc

    roles = set(payload.get("realm_access", {}).get("roles", []))
    resource_access = payload.get("resource_access", {}) or {}
    for client_data in resource_access.values():
        if isinstance(client_data, dict):
            roles.update(client_data.get("roles", []))
    sub = payload.get("sub")
    username = payload.get("preferred_username") or payload.get("username")

    if not sub or not username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token claims.")

    return TokenData(
        sub=sub,
        preferred_username=username,
        email=payload.get("email"),
        roles=roles,
        tenant_name=payload.get("tenant") or payload.get("tenant_name"),
    )
