from pydantic import BaseModel

from app.schemas.product import ProductResponse


class FavouriteAction(BaseModel):
    product_id: int


class FavouriteResponse(BaseModel):
    product: ProductResponse


class FavouriteListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int
