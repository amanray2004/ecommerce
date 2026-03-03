from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.tenant import Tenant
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.firebase_service import delete_product_image, upload_product_image
from app.services.tenant_service import TenantService


class ProductService:
    @staticmethod
    def list_products(
        db: Session,
        tenant_name: str,
        limit: int,
        offset: int,
        search: str | None,
        category: str | None,
    ) -> tuple[list[Product], int]:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        query = db.query(Product).filter(Product.tenant_id == tenant.id)

        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))

        if category:
            query = query.filter(func.lower(Product.category) == category.lower())

        total = query.count()
        items = query.order_by(Product.id.desc()).offset(offset).limit(limit).all()
        for item in items:
            item.tenant_name = tenant.name
        return items, total

    @staticmethod
    def list_all_products(
        db: Session,
        limit: int,
        offset: int,
        search: str | None,
        category: str | None,
    ) -> tuple[list[Product], int]:
        query = (
            db.query(Product, Tenant.name.label("tenant_name"))
            .join(Tenant, Tenant.id == Product.tenant_id)
            .filter(Tenant.is_active.is_(True))
        )

        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))

        if category:
            query = query.filter(func.lower(Product.category) == category.lower())

        total = query.count()
        rows = query.order_by(Product.id.desc()).offset(offset).limit(limit).all()
        items: list[Product] = []
        for product, tenant_name in rows:
            product.tenant_name = tenant_name
            items.append(product)
        return items, total

    @staticmethod
    def get_product(db: Session, tenant_name: str, product_id: int) -> Product:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant.id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        return product

    @staticmethod
    def create_product(db: Session, tenant_name: str, payload: ProductCreate, image: UploadFile) -> Product:
        if not image:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is required.")

        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        image_url, image_path = upload_product_image(tenant_name, image)

        product = Product(
            name=payload.name,
            description=payload.description,
            category=payload.category,
            price=payload.price,
            quantity=payload.quantity,
            image_url=image_url,
            image_path=image_path,
            tenant_id=tenant.id,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update_product(
        db: Session,
        tenant_name: str,
        product_id: int,
        payload: ProductUpdate,
        image: UploadFile | None,
    ) -> Product:
        product = ProductService.get_product(db, tenant_name, product_id)

        if payload.name is not None:
            product.name = payload.name
        if payload.description is not None:
            product.description = payload.description
        if payload.category is not None:
            product.category = payload.category
        if payload.price is not None:
            product.price = payload.price
        if payload.quantity is not None:
            product.quantity = payload.quantity

        if image:
            old_image_path = product.image_path
            image_url, image_path = upload_product_image(tenant_name, image)
            product.image_url = image_url
            product.image_path = image_path
            delete_product_image(old_image_path)

        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def delete_product(db: Session, tenant_name: str, product_id: int) -> None:
        product = ProductService.get_product(db, tenant_name, product_id)
        used_in_orders = db.query(OrderItem.id).filter(OrderItem.product_id == product.id).first()
        if used_in_orders:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete product because it exists in order history.",
            )

        image_path = product.image_path
        db.delete(product)
        db.commit()
        delete_product_image(image_path)
