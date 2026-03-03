from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.favourite import Favourite
from app.models.product import Product
from app.services.tenant_service import TenantService


class FavouriteService:
    @staticmethod
    def add_favourite(db: Session, tenant_name: str, user_id: str, product_id: int) -> Favourite:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant.id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

        existing = db.query(Favourite).filter(Favourite.user_id == user_id, Favourite.product_id == product_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product already marked as favourite.")

        favourite = Favourite(user_id=user_id, product_id=product_id)
        db.add(favourite)
        db.commit()
        db.refresh(favourite)
        return favourite

    @staticmethod
    def remove_favourite(db: Session, tenant_name: str, user_id: str, product_id: int) -> None:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        favourite = (
            db.query(Favourite)
            .join(Product, Product.id == Favourite.product_id)
            .filter(
                Favourite.user_id == user_id,
                Favourite.product_id == product_id,
                Product.tenant_id == tenant.id,
            )
            .first()
        )
        if not favourite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favourite not found.")

        db.delete(favourite)
        db.commit()

    @staticmethod
    def list_favourites(
        db: Session,
        tenant_name: str,
        user_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        query = (
            db.query(Product)
            .join(Favourite, Favourite.product_id == Product.id)
            .filter(Favourite.user_id == user_id, Product.tenant_id == tenant.id)
            .order_by(Product.id.desc())
        )

        total = query.count()
        items = query.offset(offset).limit(limit).all()
        for item in items:
            item.tenant_name = tenant.name
        return items, total
