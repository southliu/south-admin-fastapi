from pydantic import Field

from schemas.base import CamelModel


class ResponseModel[T](CamelModel):
    code: int = 200
    message: str = "success"
    data: T | None = None


class PageData[T](CamelModel):
    items: list[T] = Field(default_factory=list)
    page: int = 1
    page_size: int = 10
    total: int = 0
    total_pages: int = 0
