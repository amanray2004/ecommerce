from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate
from app.schemas.user import TenantUserCreate


class TenantService:
    @staticmethod
    def list_active_tenants(db: Session, limit: int, offset: int) -> tuple[list[Tenant], int]:
        query = db.query(Tenant).filter(Tenant.is_active.is_(True)).order_by(Tenant.name)
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def list_tenants(db: Session, limit: int, offset: int) -> tuple[list[Tenant], int]:
        query = db.query(Tenant).order_by(Tenant.name)
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def create_tenant(db: Session, payload: TenantCreate) -> Tenant:
        existing = db.query(Tenant).filter(Tenant.name == payload.name).first()
        if existing and existing.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant name already exists.")
        if existing and not existing.is_active:
            existing.is_active = True
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing

        tenant = Tenant(name=payload.name, is_active=True)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        return tenant

    @staticmethod
    def delete_tenant(db: Session, tenant_id: int) -> None:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
        tenant.is_active = False
        db.add(tenant)
        db.commit()

    @staticmethod
    def activate_tenant(db: Session, tenant_id: int) -> Tenant:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
        tenant.is_active = True
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        return tenant

    @staticmethod
    def get_tenant_by_name(db: Session, tenant_name: str) -> Tenant:
        tenant = db.query(Tenant).filter(Tenant.name == tenant_name, Tenant.is_active.is_(True)).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
        return tenant

    @staticmethod
    def create_tenant_user(db: Session, tenant_name: str, payload: TenantUserCreate) -> User:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)

        role = db.query(Role).filter(Role.name == payload.role_name).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")

        existing_username = db.query(User).filter(User.username == payload.username).first()
        if existing_username:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

        existing_kc = db.query(User).filter(User.keycloak_user_id == payload.keycloak_user_id).first()
        if existing_kc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Keycloak user already exists.")

        user = User(
            keycloak_user_id=payload.keycloak_user_id,
            username=payload.username,
            email=payload.email,
            role_id=role.id,
            tenant_id=tenant.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def list_tenant_users(db: Session, tenant_name: str, limit: int, offset: int) -> tuple[list[User], int]:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        query = db.query(User).filter(User.tenant_id == tenant.id).order_by(User.id)
        total = query.count()
        users = query.offset(offset).limit(limit).all()
        return users, total

    @staticmethod
    def delete_tenant_user(db: Session, tenant_name: str, user_id: int) -> None:
        tenant = TenantService.get_tenant_by_name(db, tenant_name)
        user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant user not found.")
        db.delete(user)
        db.commit()
