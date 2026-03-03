from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, enforce_tenant_access, get_db, require_roles
from app.schemas.order import OrderCreate, OrderListResponse, OrderResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/{tenant_name}/orders", tags=["orders"])
all_orders_router = APIRouter(tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    tenant_name: str,
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("platform-admin", "tenant-user", "customer")),
    _: CurrentUser = Depends(enforce_tenant_access),
):
    order = OrderService.create_order(db, tenant_name=tenant_name, user_id=current_user.keycloak_user_id, payload=payload)
    return OrderResponse.model_validate(order)


@router.get("", response_model=OrderListResponse)
def order_history(
    tenant_name: str,
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("platform-admin", "tenant-user", "customer")),
    _: CurrentUser = Depends(enforce_tenant_access),
):
    orders, total = OrderService.list_user_orders(
        db,
        tenant_name=tenant_name,
        user_id=current_user.keycloak_user_id,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(items=[OrderResponse.model_validate(order) for order in orders], total=total, limit=limit, offset=offset)


@all_orders_router.get("/orders", response_model=OrderListResponse)
def all_order_history(
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("platform-admin", "tenant-user", "customer")),
):
    orders, total = OrderService.list_user_orders_all_tenants(
        db,
        user_id=current_user.keycloak_user_id,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(items=[OrderResponse.model_validate(order) for order in orders], total=total, limit=limit, offset=offset)
