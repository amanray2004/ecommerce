from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_tenant_category", "tenant_id", "category"),
        Index("ix_products_tenant_name", "tenant_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)

    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    tenant = relationship("Tenant", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    favourites = relationship("Favourite", back_populates="product", cascade="all, delete-orphan")
