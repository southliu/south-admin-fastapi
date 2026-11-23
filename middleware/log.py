import json
import logging
from time import perf_counter

from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from config.database import AsyncSessionLocal
from schemas.log import CreateLogRequest
from services.system.log import create_log
from utils.audit import MAX_AUDIT_BYTES

logger = logging.getLogger(__name__)


class LogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http" or scope["path"] in {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }:
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        started = perf_counter()
        request_body = bytearray()
        response_body = bytearray()
        request_size = response_size = 0
        status_code = 500
        error = None

        async def receive_request() -> Message:
            nonlocal request_size
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                request_size += len(body)
                if request_size <= MAX_AUDIT_BYTES:
                    request_body.extend(body)
                else:
                    request_body.clear()
            return message

        async def send_response(message: Message) -> None:
            nonlocal status_code, response_size
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_size += len(body)
                if response_size <= MAX_AUDIT_BYTES:
                    response_body.extend(body)
                else:
                    response_body.clear()
            await send(message)

        try:
            await self.app(scope, receive_request, send_response)
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            code = getattr(request.state, "audit_code", status_code)
            if response_body:
                try:
                    payload = json.loads(response_body)
                except ValueError, UnicodeError, RecursionError:
                    payload = None
                if isinstance(payload, dict):
                    code = payload.get("code", code)
            success = error is None and isinstance(code, int) and code < 400
            params = (
                json.dumps(dict(request.query_params))
                if request.method == "GET"
                else bytes(request_body)
            )
            if request_size > MAX_AUDIT_BYTES:
                params = json.dumps({"note": "参数过长，已省略"})
            try:
                async with AsyncSessionLocal.begin() as db:
                    await create_log(
                        db,
                        CreateLogRequest(
                            username=getattr(
                                request.state, "audit_username", None
                            ),
                            method=request.method,
                            url=str(request.url),
                            params=params.decode("utf-8", errors="replace")
                            if isinstance(params, bytes)
                            else params,
                            user_agent=request.headers.get("user-agent", "")[
                                :500
                            ],
                            status="success" if success else "error",
                            error=error
                            or (None if success else f"请求失败（{code}）"),
                            latency=int((perf_counter() - started) * 1000),
                            type=1 if success else 0,
                        ),
                    )
            except SQLAlchemyError as exc:
                logger.warning("操作日志写入失败（%s）", type(exc).__name__)
