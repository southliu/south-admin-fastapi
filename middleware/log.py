import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import AsyncSessionLocal
from services.system.log import create_log
from schemas.log import CreateLogRequest
from utils.security import decode_access_token
from services.system.user import get_user_by_id


class LogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 开始时间
        start_time = time.time()

        # 获取请求信息
        method = request.method
        url = str(request.url)

        # 跳过不需要记录的路径
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        if any(path in url for path in skip_paths):
            return await call_next(request)

        # 获取请求参数
        params = None
        try:
            if method == "GET":
                params = str(dict(request.query_params)) if request.query_params else None
            else:
                body = await request.body()
                if body:
                    params = body.decode("utf-8")
        except Exception:
            params = None

        # 获取客户端 IP
        ip = request.client.host if request.client else None

        # 获取 User-Agent
        user_agent = request.headers.get("user-agent", None)

        # 获取当前用户
        username = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        async with AsyncSessionLocal() as db:
                            user = await get_user_by_id(db, int(user_id))
                            if user:
                                username = user.username
        except Exception:
            pass

        # 执行请求
        response = None
        status = "success"
        error = None

        try:
            response = await call_next(request)
            status = "success" if response.status_code < 400 else "error"
        except Exception as e:
            status = "error"
            error = str(e)
            raise
        finally:
            # 计算耗时
            latency = int((time.time() - start_time) * 1000)

            # 确定日志类型
            log_type = 1 if status == "success" else 0

            # 记录日志
            try:
                async with AsyncSessionLocal() as db:
                    log_data = CreateLogRequest(
                        username=username,
                        ip=ip,
                        method=method,
                        url=url,
                        params=params,
                        user_agent=user_agent,
                        status=status,
                        error=error,
                        latency=latency,
                        type=log_type,
                    )
                    await create_log(db, log_data)
            except Exception:
                # 日志记录失败不影响正常请求
                pass

        return response
