from app.routers.admin import router as admin_router
from app.routers.favourites import router as favourites_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router

__all__ = ["admin_router", "products_router", "orders_router", "favourites_router"]
