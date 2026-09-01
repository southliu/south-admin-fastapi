from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import READONLY_ENABLED

# 只读模式下仍放行的方法：GET 查询；HEAD/OPTIONS 是浏览器语义请求与 CORS 预检，
# 拦掉 OPTIONS 会导致前端连 GET 都发不出去
ALLOWED_METHODS = {"GET", "HEAD", "OPTIONS"}

# 只读模式下仍放行的路径：登录
ALLOWED_PATHS = {"/system/user/login"}


class ReadOnlyMiddleware(BaseHTTPMiddleware):
    """只读模式中间件：config.yaml readonly.enabled 为 1 时，
    除登录外的非 GET 请求一律拒绝，返回 {code: 403}（HTTP 恒为 200，前端约定）。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if (
            READONLY_ENABLED == 1
            and request.method.upper() not in ALLOWED_METHODS
            and request.url.path not in ALLOWED_PATHS
        ):
            return JSONResponse(
                status_code=200,
                content={
                    "code": 500,
                    "data": "",
                    "message": "系统处于只读模式，仅允许查询和登录操作",
                },
            )
        return await call_next(request)
