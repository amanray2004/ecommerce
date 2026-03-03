"""use keycloak subject as order/favourite user_id

Revision ID: 20260302_0002
Revises: 20260301_0001
Create Date: 2026-03-02 00:02:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260302_0002"
down_revision = "20260301_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE favourites DROP CONSTRAINT IF EXISTS favourites_user_id_fkey")
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_user_id_fkey")

    op.alter_column("favourites", "user_id", existing_type=sa.Integer(), type_=sa.String(length=128), nullable=False)
    op.alter_column("orders", "user_id", existing_type=sa.Integer(), type_=sa.String(length=128), nullable=False)


def downgrade() -> None:
    op.alter_column("orders", "user_id", existing_type=sa.String(length=128), type_=sa.Integer(), nullable=False)
    op.alter_column("favourites", "user_id", existing_type=sa.String(length=128), type_=sa.Integer(), nullable=False)

    op.create_foreign_key("orders_user_id_fkey", "orders", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("favourites_user_id_fkey", "favourites", "users", ["user_id"], ["id"], ondelete="CASCADE")
