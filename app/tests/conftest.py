import os
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test_ecommerce.db"
os.environ["KEYCLOAK_PUBLIC_KEY"] = "test"
os.environ["SEED_ROLES_ON_STARTUP"] = "false"
os.environ["RUN_STARTUP_TASKS"] = "false"

from app.core.dependencies import get_current_user, get_db  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Product, Role, Tenant, User  # noqa: E402

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_ecommerce.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_app():
    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.state.test_user = SimpleNamespace(
        id=1,
        username="admin",
        role_name="platform-admin",
        token_tenant=None,
        tenant_id=None,
    )

    def override_current_user():
        return app.state.test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    return app


@pytest.fixture
def auth_user_setter():
    def _set_user(
        app,
        *,
        user_id: int,
        username: str,
        role_name: str,
        token_tenant: str | None,
        tenant_id: int | None = None,
    ):
        app.state.test_user = SimpleNamespace(
            id=user_id,
            username=username,
            role_name=role_name,
            token_tenant=token_tenant,
            tenant_id=tenant_id,
        )

    return _set_user


@pytest.fixture(autouse=True)
def seed_data():
    db_session = TestingSessionLocal()
    db_session.query(Product).delete()
    db_session.query(User).delete()
    db_session.query(Role).delete()
    db_session.query(Tenant).delete()
    db_session.commit()

    role_admin = Role(name="platform-admin")
    role_tenant = Role(name="tenant-user")
    role_customer = Role(name="customer")
    db_session.add_all([role_admin, role_tenant, role_customer])
    db_session.flush()

    tenant_a = Tenant(name="brand-a", is_active=True)
    tenant_b = Tenant(name="brand-b", is_active=True)
    db_session.add_all([tenant_a, tenant_b])
    db_session.flush()

    admin = User(
        keycloak_user_id="kc-admin",
        username="admin",
        email="admin@example.com",
        role_id=role_admin.id,
        tenant_id=None,
    )
    tenant_user = User(
        keycloak_user_id="kc-tenant",
        username="tenant_user",
        email="tenant@example.com",
        role_id=role_tenant.id,
        tenant_id=tenant_a.id,
    )
    customer = User(
        keycloak_user_id="kc-customer",
        username="customer_user",
        email="customer@example.com",
        role_id=role_customer.id,
        tenant_id=tenant_a.id,
    )
    db_session.add_all([admin, tenant_user, customer])
    db_session.flush()

    products = [
        Product(
            name="Alpha Shoe",
            description="A",
            category="Footwear",
            price=100,
            quantity=10,
            image_url="https://example.com/a.jpg",
            image_path="brand-a/products/a.jpg",
            tenant_id=tenant_a.id,
        ),
        Product(
            name="Alpha Shirt",
            description="B",
            category="Apparel",
            price=50,
            quantity=5,
            image_url="https://example.com/b.jpg",
            image_path="brand-a/products/b.jpg",
            tenant_id=tenant_a.id,
        ),
        Product(
            name="Bravo Shoe",
            description="C",
            category="Footwear",
            price=90,
            quantity=3,
            image_url="https://example.com/c.jpg",
            image_path="brand-b/products/c.jpg",
            tenant_id=tenant_b.id,
        ),
    ]
    db_session.add_all(products)
    db_session.commit()
    db_session.close()

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "admin": admin,
        "tenant_user": tenant_user,
        "customer": customer,
        "products": products,
    }
