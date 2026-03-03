from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, get_db, require_roles
from app.schemas.tenant import TenantCreate, TenantResponse
from app.schemas.user import TenantUserCreate, UserListResponse, UserResponse
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tenants")
def list_tenants(
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin")),
):
    items, total = TenantService.list_tenants(db, limit=limit, offset=offset)
    return {
        "items": [TenantResponse.model_validate(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin")),
):
    tenant = TenantService.create_tenant(db, payload)
    return TenantResponse.model_validate(tenant)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin")),
):
    TenantService.delete_tenant(db, tenant_id)


@router.patch("/tenants/{tenant_id}/activate", response_model=TenantResponse)
def activate_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin")),
):
    tenant = TenantService.activate_tenant(db, tenant_id)
    return TenantResponse.model_validate(tenant)


@router.post("/tenants/{tenant_name}/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_tenant_user(
    tenant_name: str,
    payload: TenantUserCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin")),
):
    user = TenantService.create_tenant_user(db, tenant_name, payload)
    return UserResponse(
        id=user.id,
        keycloak_user_id=user.keycloak_user_id,
        username=user.username,
        email=user.email,
        role_name=user.role.name,
        tenant_id=user.tenant_id,
    )


@router.get("/tenants/{tenant_name}/users", response_model=UserListResponse)
def list_tenant_users(
    tenant_name: str,
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin")),
):
    users, total = TenantService.list_tenant_users(db, tenant_name, limit=limit, offset=offset)
    return UserListResponse(
        items=[
            UserResponse(
                id=user.id,
                keycloak_user_id=user.keycloak_user_id,
                username=user.username,
                email=user.email,
                role_name=user.role.name,
                tenant_id=user.tenant_id,
            )
            for user in users
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/tenants/{tenant_name}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant_user(
    tenant_name: str,
    user_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin")),
):
    TenantService.delete_tenant_user(db, tenant_name, user_id)
