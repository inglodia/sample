from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.auth import UserOut


class UserListOut(BaseModel):
    items: list[UserOut]


class RolePatchIn(BaseModel):
    role: str = Field(pattern=r"^(admin|user)$")
