from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import READONLY_ENABLED

# 浏览器预检和 HEAD 请求也需要放行。
ALLOWED_METHODS = {"GET", "HEAD", "OPTIONS"}

# 只读模式下仍放行的路径：登录
ALLOWED_PATHS = {"/system/user/login"}


class ReadOnlyMiddleware(BaseHTTPMiddleware):
    """只读模式拒绝写入，返回 HTTP 200 和业务码 500。"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if (
            READONLY_ENABLED == 1
            and request.method.upper() not in ALLOWED_METHODS
            and request.url.path not in ALLOWED_PATHS
        ):
            request.state.audit_code = 500
            return JSONResponse(
                status_code=200,
                content={
                    "code": 500,
                    "data": "",
                    "message": "系统处于只读模式，仅允许查询和登录操作",
                },
            )
        return await call_next(request)
