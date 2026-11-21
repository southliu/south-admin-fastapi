from pydantic import Field

from schemas.base import CamelModel
from schemas.fields import Description


class CreatePermissionRequest(CamelModel):
    name: str = Field(min_length=1, max_length=100)
    description: Description | None = None


class UpdatePermissionRequest(CamelModel):
    name: str = Field(min_length=1, max_length=100)
    description: Description | None = None
