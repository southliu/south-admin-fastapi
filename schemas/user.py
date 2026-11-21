from __future__ import annotations

from typing import Literal

from pydantic import EmailStr, Field, PositiveInt

from schemas.base import CamelModel
from schemas.fields import Password


class LoginRequest(CamelModel):
    username: str = Field(min_length=1, max_length=100)
    password: Password


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
    email: EmailStr | None = None
    status: int
    roles: list[int] = Field(default_factory=list)


class CreateUserRequest(CamelModel):
    username: str = Field(min_length=1, max_length=100)
    password: Password
    name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    status: Literal[0, 1] = 1
    role_ids: list[PositiveInt] = Field(default_factory=list, max_length=100)


class UpdateUserRequest(CamelModel):
    username: str = Field(min_length=1, max_length=100)
    password: Password | None = None
    name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    status: Literal[0, 1]
    role_ids: list[PositiveInt] = Field(max_length=100)


class UpdatePasswordRequest(CamelModel):
    old_password: Password
    new_password: Password
    confirm_password: Password


class RefreshPermissionsResponse(CamelModel):
    user: UserInfo
    permissions: list[str]
    roles: list[int]
