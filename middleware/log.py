import json
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from urllib.parse import parse_qsl

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.database import AsyncSessionLocal
from config.settings import settings
from schemas.log import CreateLogRequest
from services.system.log import create_log

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "accesstoken",
    "authorization",
    "confirmpassword",
    "newpassword",
    "oldpassword",
    "password",
    "refreshtoken",
    "secret",
    "token",
}
SKIP_PATHS = {
    "/docs",
    "/favicon.ico",
    "/health",
    "/openapi.json",
    "/redoc",
}


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): (
                "***"
                if "".join(
                    character
                    for character in str(key).casefold()
                    if character.isalnum()
                )
                in SENSITIVE_KEYS
                else redact_sensitive_data(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    return value


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}…"


async def _read_request_params(request: Request) -> str | None:
    limit = settings.log.request_body_limit
    if limit == 0:
        return None

    if request.method == "GET":
        params = redact_sensitive_data(dict(request.query_params))
        return json.dumps(params, ensure_ascii=False) if params else None

    content_length = request.headers.get("content-length")
    if content_length is None or int(content_length) > limit:
        return "<body omitted>"

    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" in content_type:
        return "<multipart body omitted>"

    body = await request.body()
    if not body:
        return None

    if "application/json" in content_type:
        try:
            value = redact_sensitive_data(json.loads(body))
        except UnicodeDecodeError, json.JSONDecodeError:
            return "<invalid json body>"
        return _truncate(json.dumps(value, ensure_ascii=False), limit)

    if "application/x-www-form-urlencoded" in content_type:
        form = dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))
        value = redact_sensitive_data(form)
        return _truncate(json.dumps(value, ensure_ascii=False), limit)

    return "<body omitted>"


class LogMiddleware(BaseHTTPMiddleware):
    """记录经过脱敏和截断的操作日志。"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()
        try:
            params = await _read_request_params(request)
        except UnicodeDecodeError, ValueError:
            params = "<unreadable body>"

        response: Response | None = None
        status = "success"
        error: str | None = None
        try:
            response = await call_next(request)
            error = getattr(request.state, "operation_error", None)
            status = (
                "success"
                if response.status_code < 400 and error is None
                else "error"
            )
            return response
        except Exception as exc:
            status = "error"
            error = type(exc).__name__
            raise
        finally:
            latency = int((time.perf_counter() - start_time) * 1000)
            log_data = CreateLogRequest(
                username=getattr(request.state, "current_username", None),
                ip=request.client.host if request.client else None,
                method=request.method,
                url=str(request.url.replace(query="")),
                params=params,
                user_agent=request.headers.get("user-agent"),
                status=status,
                error=error,
                latency=latency,
                type=1 if status == "success" else 0,
            )
            try:
                async with AsyncSessionLocal.begin() as db:
                    await create_log(db, log_data)
            except Exception:
                logger.exception("写入操作日志失败")
