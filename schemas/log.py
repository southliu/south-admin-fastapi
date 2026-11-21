from typing import Literal

from pydantic import Field

from schemas.base import CamelModel
from schemas.fields import TextContent


class CreateLogRequest(CamelModel):
    username: str | None = Field(default=None, max_length=100)
    ip: str | None = Field(default=None, max_length=50)
    method: str | None = Field(default=None, max_length=10)
    url: str | None = Field(default=None, max_length=500)
    params: TextContent | None = None
    user_agent: str | None = Field(default=None, max_length=500)
    status: Literal["success", "error"] | None = None
    error: TextContent | None = None
    latency: int = Field(default=0, ge=0)
    type: Literal[0, 1, 2, 3] = 0
