from pydantic import BaseModel, Field


class TenantUserCreate(BaseModel):
    keycloak_user_id: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=3, max_length=100)
    email: str | None = None
    role_name: str = Field(pattern="^(tenant-user|customer)$")


class UserResponse(BaseModel):
    id: int
    keycloak_user_id: str
    username: str
    email: str | None
    role_name: str
    tenant_id: int | None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class UserSyncPayload(BaseModel):
    """Payload used internally for syncing authenticated Keycloak users to local DB."""

    keycloak_user_id: str
    username: str
    email: str | None
    role_name: str
    tenant_id: int | None
