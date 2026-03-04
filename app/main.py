from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Role
from app.routers.admin import router as admin_router
from app.routers.favourites import router as favourites_router
from app.routers.orders import all_orders_router, router as orders_router
from app.routers.products import all_products_router, router as products_router
from app.routers.tenants import router as tenants_router
from app.services.firebase_service import initialize_firebase


def _seed_roles(db: Session) -> None:
    required_roles = {"platform-admin", "tenant-user", "customer"}
    existing = {r.name for r in db.query(Role).all()}
    for role_name in required_roles - existing:
        db.add(Role(name=role_name))
    db.commit()


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if not settings.run_startup_tasks:
            yield
            return

        # Keep automatic DDL optional; production should run Alembic migrations.
        if settings.auto_create_tables:
            Base.metadata.create_all(bind=engine)
        if settings.seed_roles_on_startup:
            with SessionLocal() as db:
                _seed_roles(db)
        initialize_firebase()
        yield

    swagger_oauth_config = {}
    if settings.keycloak_client_id:
        swagger_oauth_config = {
            "clientId": settings.keycloak_client_id,
            "usePkceWithAuthorizationCodeGrant": True,
        }

    app = FastAPI(title=settings.app_name, lifespan=lifespan, swagger_ui_init_oauth=swagger_oauth_config)
    Path("uploads").mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    origin_regex = settings.cors_allow_origin_regex or None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    app.include_router(admin_router)
    app.include_router(tenants_router)
    app.include_router(all_products_router)
    app.include_router(all_orders_router)
    app.include_router(products_router)
    app.include_router(orders_router)
    app.include_router(favourites_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
