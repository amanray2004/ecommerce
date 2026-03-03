from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, enforce_tenant_access, get_db, require_roles
from app.schemas.favourite import FavouriteAction, FavouriteListResponse
from app.schemas.product import ProductResponse
from app.services.favourite_service import FavouriteService

router = APIRouter(prefix="/{tenant_name}/favourites", tags=["favourites"])


@router.post("", status_code=status.HTTP_201_CREATED)
def add_favourite(
    tenant_name: str,
    payload: FavouriteAction,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("platform-admin", "tenant-user", "customer")),
    _: CurrentUser = Depends(enforce_tenant_access),
):
    favourite = FavouriteService.add_favourite(db, tenant_name, current_user.keycloak_user_id, payload.product_id)
    return {"id": favourite.id, "product_id": favourite.product_id}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favourite(
    tenant_name: str,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("platform-admin", "tenant-user", "customer")),
    _: CurrentUser = Depends(enforce_tenant_access),
):
    FavouriteService.remove_favourite(db, tenant_name, current_user.keycloak_user_id, product_id)


@router.get("", response_model=FavouriteListResponse)
def list_favourites(
    tenant_name: str,
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("platform-admin", "tenant-user", "customer")),
    _: CurrentUser = Depends(enforce_tenant_access),
):
    items, total = FavouriteService.list_favourites(db, tenant_name, current_user.keycloak_user_id, limit=limit, offset=offset)
    return FavouriteListResponse(
        items=[ProductResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
