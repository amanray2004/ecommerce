from collections.abc import Callable

from fastapi import Depends, HTTPException, Path, Security, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import TokenData, decode_and_validate_token
from app.db.session import SessionLocal


class CurrentUser:
    """Authenticated user context derived from Keycloak token only."""

    def __init__(self, token: TokenData, role_name: str):
        self.id = token.sub
        self.username = token.preferred_username
        self.email = token.email
        self.keycloak_user_id = token.sub
        self.tenant_id = None
        self.role_name = role_name
        self.token_roles = token.roles
        self.token_tenant = token.tenant_name


settings = get_settings()
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.keycloak_issuer.rstrip('/')}/protocol/openid-connect/auth"
    if settings.keycloak_issuer
    else "",
    tokenUrl=f"{settings.keycloak_issuer.rstrip('/')}/protocol/openid-connect/token"
    if settings.keycloak_issuer
    else "",
    auto_error=False,
)


def _role_variants(role_name: str) -> set[str]:
    normalized = role_name.strip().lower()
    variants = {normalized}
    variants.add(normalized.replace("-", "_"))
    variants.add(normalized.replace("_", "-"))
    return variants


def _has_any_role(token_roles: set[str], *target_roles: str) -> bool:
    normalized_token_roles = {r.lower() for r in token_roles}
    for target in target_roles:
        if _role_variants(target) & normalized_token_roles:
            return True
    return False


def _is_platform_admin(token_roles: set[str]) -> bool:
    normalized = {r.lower() for r in token_roles}
    admin_aliases = {"platform-admin", "platform_admin", "admin", "superadmin", "super-admin"}
    if normalized & admin_aliases:
        return True
    return any("platform-admin" in r or "platform_admin" in r for r in normalized)


def _is_tenant_user(token_roles: set[str]) -> bool:
    normalized = {r.lower() for r in token_roles}
    tenant_aliases = {"tenant-user", "tenant_user", "tenant"}
    if normalized & tenant_aliases:
        return True
    return any("tenant-user" in r or "tenant_user" in r for r in normalized)


def _extract_bearer_token(token: str | None) -> str:
    if not token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing bearer token.")
    return token.strip()


def _derive_role_name(token_roles: set[str]) -> str:
    if _is_platform_admin(token_roles):
        return "platform-admin"
    if _is_tenant_user(token_roles):
        return "tenant-user"
    return "customer"


def get_current_user(token: str | None = Security(oauth2_scheme)) -> CurrentUser:
    settings = get_settings()
    bearer_token = _extract_bearer_token(token)
    token_data = decode_and_validate_token(bearer_token)

    if settings.keycloak_issuer and not token_data.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token issuer.")

    role_name = _derive_role_name(token_data.roles)
    return CurrentUser(token=token_data, role_name=role_name)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        allowed = {role.lower() for role in allowed_roles}
        token_role_ok = False

        if "platform-admin" in allowed and _is_platform_admin(current_user.token_roles):
            token_role_ok = True
        if "tenant-user" in allowed and _is_tenant_user(current_user.token_roles):
            token_role_ok = True
        if "customer" in allowed and _has_any_role(current_user.token_roles, "customer", "user"):
            token_role_ok = True

        if current_user.role_name.lower() in allowed:
            token_role_ok = True

        if not token_role_ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions.")
        return current_user

    return dependency


def enforce_tenant_access(
    tenant_name: str = Path(..., min_length=2),
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Tenant enforcement for shopping flow: cross-tenant allowed for authenticated users."""

    # Platform-admin can always access.
    if current_user.role_name == "platform-admin":
        return current_user

    # Customer and tenant-user are both allowed to shop/order across tenants.
    # Domain-level write restrictions are enforced separately on management routes.
    return current_user


def enforce_tenant_management_access(
    tenant_name: str = Path(..., min_length=2),
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Strict tenant enforcement for management flow (product write operations)."""

    if current_user.role_name == "platform-admin":
        return current_user

    if current_user.role_name == "tenant-user":
        if not current_user.token_tenant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant claim is required for tenant routes.")
        if current_user.token_tenant != tenant_name:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch in token and path.")
        return current_user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions.")
