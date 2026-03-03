from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, get_db, require_roles
from app.schemas.tenant import TenantResponse
from app.services.tenant_service import TenantService

router = APIRouter(tags=["tenants"])


@router.get("/tenants")
def list_active_tenants(
    limit: int = Query(default=get_settings().default_page_limit, ge=1, le=get_settings().max_page_limit),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles("platform-admin", "tenant-user", "customer")),
):
    items, total = TenantService.list_active_tenants(db, limit=limit, offset=offset)
    return {
        "items": [TenantResponse.model_validate(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

