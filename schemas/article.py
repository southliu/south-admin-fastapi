from typing import Optional

from schemas.base import CamelModel


class CreateArticleRequest(CamelModel):
    title: str
    author: Optional[str] = None
    content: Optional[str] = None
    demo: Optional[dict] = None


class UpdateArticleRequest(CamelModel):
    title: str
    author: Optional[str] = None
    content: Optional[str] = None
    demo: Optional[dict] = None
