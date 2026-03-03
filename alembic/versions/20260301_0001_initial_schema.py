"""initial schema

Revision ID: 20260301_0001
Revises: 
Create Date: 2026-03-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260301_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keycloak_user_id", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_users_keycloak_user_id", "users", ["keycloak_user_id"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("image_path", sa.String(length=500), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_products_name", "products", ["name"], unique=False)
    op.create_index("ix_products_category", "products", ["category"], unique=False)
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"], unique=False)
    op.create_index("ix_products_tenant_category", "products", ["tenant_id", "category"], unique=False)
    op.create_index("ix_products_tenant_name", "products", ["tenant_id", "name"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_quantity", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"], unique=False)
    op.create_index("ix_orders_tenant_id", "orders", ["tenant_id"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_at_purchase", sa.Numeric(10, 2), nullable=False),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_product"),
    )

    op.create_table(
        "favourites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", name="uq_favourite_user_product"),
    )
    op.create_index("ix_favourites_user_id", "favourites", ["user_id"], unique=False)
    op.create_index("ix_favourites_product_id", "favourites", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_favourites_product_id", table_name="favourites")
    op.drop_index("ix_favourites_user_id", table_name="favourites")
    op.drop_table("favourites")

    op.drop_table("order_items")

    op.drop_index("ix_orders_tenant_id", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")

    op.drop_index("ix_products_tenant_name", table_name="products")
    op.drop_index("ix_products_tenant_category", table_name="products")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_keycloak_user_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_tenants_name", table_name="tenants")
    op.drop_table("tenants")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
