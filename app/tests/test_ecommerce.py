import pytest
from fastapi import HTTPException

from app.core.dependencies import CurrentUser, enforce_tenant_access, enforce_tenant_management_access, require_roles
from app.core.security import TokenData
from app.models import Favourite, Product, User
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.favourite_service import FavouriteService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.tests.conftest import TestingSessionLocal


def test_role_restriction_admin_route(seed_data):
    db = TestingSessionLocal()
    customer = db.query(User).filter(User.username == "customer_user").first()
    token = TokenData(
        sub=customer.keycloak_user_id,
        preferred_username=customer.username,
        email=customer.email,
        roles={"customer"},
        tenant_name="brand-a",
    )
    current_user = CurrentUser(token, "customer")

    dep = require_roles("platform-admin")
    with pytest.raises(HTTPException) as exc:
        dep(current_user)

    assert exc.value.status_code == 403
    db.close()


def test_tenant_user_cross_tenant_shop_allowed(seed_data):
    db = TestingSessionLocal()
    tenant_user = db.query(User).filter(User.username == "tenant_user").first()
    token = TokenData(
        sub=tenant_user.keycloak_user_id,
        preferred_username=tenant_user.username,
        email=tenant_user.email,
        roles={"tenant-user"},
        tenant_name="brand-a",
    )
    current_user = CurrentUser(token, "tenant-user")

    allowed_user = enforce_tenant_access(tenant_name="brand-b", current_user=current_user)
    assert allowed_user is current_user
    db.close()


def test_tenant_mismatch_blocked_for_management(seed_data):
    db = TestingSessionLocal()
    tenant_user = db.query(User).filter(User.username == "tenant_user").first()
    token = TokenData(
        sub=tenant_user.keycloak_user_id,
        preferred_username=tenant_user.username,
        email=tenant_user.email,
        roles={"tenant-user"},
        tenant_name="brand-a",
    )
    current_user = CurrentUser(token, "tenant-user")

    with pytest.raises(HTTPException) as exc:
        enforce_tenant_management_access(tenant_name="brand-b", current_user=current_user)

    assert exc.value.status_code == 403
    db.close()


def test_search_products_partial_name(seed_data):
    db = TestingSessionLocal()
    items, total = ProductService.list_products(
        db,
        tenant_name="brand-a",
        limit=20,
        offset=0,
        search="shoe",
        category=None,
    )

    assert total == 1
    assert items[0].name == "Alpha Shoe"
    db.close()


def test_pagination_products(seed_data):
    db = TestingSessionLocal()
    items, total = ProductService.list_products(
        db,
        tenant_name="brand-a",
        limit=1,
        offset=1,
        search=None,
        category=None,
    )

    assert total == 2
    assert len(items) == 1
    db.close()


def test_order_creation_success_and_stock_deduction(seed_data):
    db = TestingSessionLocal()
    customer = db.query(User).filter(User.username == "customer_user").first()
    product1 = db.query(Product).filter(Product.name == "Alpha Shoe").first()
    product2 = db.query(Product).filter(Product.name == "Alpha Shirt").first()

    order = OrderService.create_order(
        db,
        tenant_name="brand-a",
        user_id=customer.keycloak_user_id,
        payload=OrderCreate(
            items=[
                OrderItemCreate(product_id=product1.id, quantity=2),
                OrderItemCreate(product_id=product2.id, quantity=1),
            ]
        ),
    )

    assert order.total_quantity == 3
    assert float(order.total_amount) == 250.0

    updated = db.query(Product).filter(Product.id == product1.id).first()
    assert updated.quantity == 8
    db.close()


def test_order_creation_fails_on_insufficient_stock(seed_data):
    db = TestingSessionLocal()
    customer = db.query(User).filter(User.username == "customer_user").first()
    product2 = db.query(Product).filter(Product.name == "Alpha Shirt").first()

    with pytest.raises(HTTPException) as exc:
        OrderService.create_order(
            db,
            tenant_name="brand-a",
            user_id=customer.keycloak_user_id,
            payload=OrderCreate(items=[OrderItemCreate(product_id=product2.id, quantity=100)]),
        )

    assert exc.value.status_code == 400
    assert "Alpha Shirt" in exc.value.detail
    assert "available" in exc.value.detail
    db.close()


def test_product_delete_conflict_when_used_in_order(seed_data):
    db = TestingSessionLocal()
    customer = db.query(User).filter(User.username == "customer_user").first()
    product = db.query(Product).filter(Product.name == "Alpha Shoe").first()

    OrderService.create_order(
        db,
        tenant_name="brand-a",
        user_id=customer.keycloak_user_id,
        payload=OrderCreate(items=[OrderItemCreate(product_id=product.id, quantity=1)]),
    )

    with pytest.raises(HTTPException) as exc:
        ProductService.delete_product(db, "brand-a", product.id)

    assert exc.value.status_code == 409
    assert "order history" in exc.value.detail
    db.close()


def test_favourite_add_remove_and_list(seed_data):
    db = TestingSessionLocal()
    customer = db.query(User).filter(User.username == "customer_user").first()
    product1 = db.query(Product).filter(Product.name == "Alpha Shoe").first()

    favourite = FavouriteService.add_favourite(db, "brand-a", customer.keycloak_user_id, product1.id)
    assert favourite.id is not None

    items, total = FavouriteService.list_favourites(db, "brand-a", customer.keycloak_user_id, limit=10, offset=0)
    assert total == 1
    assert items[0].id == product1.id

    FavouriteService.remove_favourite(db, "brand-a", customer.keycloak_user_id, product1.id)
    left = db.query(Favourite).filter(Favourite.user_id == customer.keycloak_user_id, Favourite.product_id == product1.id).first()
    assert left is None
    db.close()
