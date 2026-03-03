from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import (
    CurrentUser,
    enforce_tenant_access,
    enforce_tenant_management_access,
    get_db,
    get_current_user,
    require_roles,
)
from app.schemas.product import ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/{tenant_name}/products", tags=["products"])
all_products_router = APIRouter(tags=["products"])


@all_products_router.get("/products", response_model=ProductListResponse)
def list_all_products(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    items, total = ProductService.list_all_products(
        db,
        limit=limit,
        offset=offset,
        search=search,
        category=category,
    )
    return ProductListResponse(items=[ProductResponse.model_validate(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("", response_model=ProductListResponse)
def list_products(
    tenant_name: str,
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(enforce_tenant_access),
):
    items, total = ProductService.list_products(
        db,
        tenant_name=tenant_name,
        limit=limit,
        offset=offset,
        search=search,
        category=category,
    )
    return ProductListResponse(items=[ProductResponse.model_validate(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    tenant_name: str,
    product_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(enforce_tenant_access),
):
    product = ProductService.get_product(db, tenant_name, product_id)
    return ProductResponse.model_validate(product)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    tenant_name: str,
    name: str = Form(...),
    description: str | None = Form(default=None),
    category: str = Form(...),
    price: Decimal = Form(...),
    quantity: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("tenant-user")),
    __: CurrentUser = Depends(enforce_tenant_management_access),
):
    payload = ProductCreate(name=name, description=description, category=category, price=price, quantity=quantity)
    product = ProductService.create_product(db, tenant_name, payload, image)
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    tenant_name: str,
    product_id: int,
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    category: str | None = Form(default=None),
    price: Decimal | None = Form(default=None),
    quantity: int | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("tenant-user")),
    __: CurrentUser = Depends(enforce_tenant_management_access),
):
    payload = ProductUpdate(
        name=name,
        description=description,
        category=category,
        price=price,
        quantity=quantity,
    )
    product = ProductService.update_product(db, tenant_name, product_id, payload, image)
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    tenant_name: str,
    product_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("tenant-user")),
    __: CurrentUser = Depends(enforce_tenant_management_access),
):
    ProductService.delete_product(db, tenant_name, product_id)
