from typing import Any

from pydantic import Field

from schemas.base import CamelModel
from schemas.fields import TextContent


class CreateArticleRequest(CamelModel):
    title: str = Field(min_length=1, max_length=200)
    author: str | None = Field(default=None, max_length=100)
    content: TextContent | None = None
    demo: dict[str, Any] | None = None


class UpdateArticleRequest(CamelModel):
    title: str = Field(min_length=1, max_length=200)
    author: str | None = Field(default=None, max_length=100)
    content: TextContent | None = None
    demo: dict[str, Any] | None = None
