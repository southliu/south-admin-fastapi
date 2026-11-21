from typing import Literal

from pydantic import Field, PositiveInt

from schemas.base import CamelModel

MenuAction = Literal[
    "create",
    "delete",
    "detail",
    "export",
    "status",
    "update",
]


class CreateMenuRequest(CamelModel):
    label: str = Field(min_length=1, max_length=50)
    label_en: str = Field(min_length=1, max_length=50)
    type: Literal[1, 2, 3]
    icon: str | None = Field(default=None, max_length=100)
    router: str | None = Field(default=None, max_length=255)
    rule: str | None = Field(default=None, max_length=100)
    order: int = Field(default=0, ge=0)
    state: Literal[0, 1] = 1
    parent_id: PositiveInt | None = None
    actions: list[MenuAction] = Field(default_factory=list, max_length=20)


class UpdateMenuRequest(CamelModel):
    label: str = Field(min_length=1, max_length=50)
    label_en: str = Field(min_length=1, max_length=50)
    type: Literal[1, 2, 3]
    icon: str | None = Field(default=None, max_length=100)
    router: str | None = Field(default=None, max_length=255)
    rule: str | None = Field(default=None, max_length=100)
    order: int = Field(ge=0)
    state: Literal[0, 1]
    parent_id: PositiveInt | None = None


class ChangeMenuStateRequest(CamelModel):
    id: PositiveInt
    state: Literal[0, 1]


class BatchDeleteRequest(CamelModel):
    ids: list[PositiveInt] = Field(min_length=1, max_length=100)
