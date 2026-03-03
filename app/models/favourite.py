from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Favourite(Base):
    __tablename__ = "favourites"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_favourite_user_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    product = relationship("Product", back_populates="favourites")
