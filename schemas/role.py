from pydantic import Field, PositiveInt

from schemas.base import CamelModel
from schemas.fields import Description


class CreateRoleRequest(CamelModel):
    name: str = Field(min_length=1, max_length=50)
    description: Description | None = None
    authorize: list[PositiveInt] | None = Field(default=None, max_length=500)


class UpdateRoleRequest(CamelModel):
    name: str = Field(min_length=1, max_length=50)
    description: Description | None = None
    authorize: list[PositiveInt] = Field(max_length=500)


class AuthorizeRoleRequest(CamelModel):
    role_id: PositiveInt
    menu_ids: list[PositiveInt] = Field(max_length=500)
