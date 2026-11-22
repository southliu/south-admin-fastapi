from pydantic import Field

from schemas.base import CamelModel


class LoginRequest(CamelModel):
    username: str
    password: str


class LoginResponse(CamelModel):
    token: str
    user: UserInfo
    roles: list[int]
    permissions: list[str]


class UserInfo(CamelModel):
    id: int
    username: str
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: int
    roles: list[int] = Field(default_factory=list)


class CreateUserRequest(CamelModel):
    username: str
    password: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: int = 1
    role_ids: list[int] = Field(default_factory=list)


class UpdateUserRequest(CamelModel):
    username: str
    password: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: int | None = None
    role_ids: list[int] | None = None


class UpdatePasswordRequest(CamelModel):
    old_password: str
    new_password: str
    confirm_password: str


class RefreshPermissionsResponse(CamelModel):
    user: UserInfo
    permissions: list[str]
    roles: list[int]


class UserPageQuery(CamelModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    username: str | None = None
    email: str | None = None
    phone: str | None = None
