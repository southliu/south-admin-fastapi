from schemas.base import CamelModel


class CreateLogRequest(CamelModel):
    username: str | None = None
    method: str | None = None
    url: str | None = None
    params: str | None = None
    user_agent: str | None = None
    status: str | None = None
    error: str | None = None
    latency: int = 0
    type: int = 0
