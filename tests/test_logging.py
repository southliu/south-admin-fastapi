import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import Request
from fastapi.responses import JSONResponse

from middleware import log as log_middleware
from middleware.log import (
    LogMiddleware,
    _read_request_params,
    redact_sensitive_data,
)


def test_redact_sensitive_data_recursively() -> None:
    value = {
        "username": "admin",
        "password": "secret",
        "nested": {"access_token": "token", "safe": "value"},
    }

    assert redact_sensitive_data(value) == {
        "username": "admin",
        "password": "***",
        "nested": {"access_token": "***", "safe": "value"},
    }


async def test_json_request_body_is_redacted() -> None:
    body = json.dumps(
        {
            "username": "admin",
            "password": "secret",
            "confirmPassword": "secret",
        }
    ).encode()
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/system/user/login",
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("test", 50000),
        },
        receive,
    )

    result = await _read_request_params(request)

    assert result is not None
    assert "secret" not in result
    assert result.count("***") == 2


async def test_business_error_response_is_logged_as_error(
    monkeypatch,
) -> None:
    saved_log = AsyncMock()

    class Transaction:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(log_middleware, "create_log", saved_log)
    monkeypatch.setattr(
        log_middleware,
        "AsyncSessionLocal",
        SimpleNamespace(begin=Transaction),
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("test", 50000),
        }
    )

    async def call_next(current_request):
        current_request.state.operation_error = "ForbiddenError"
        return JSONResponse(
            status_code=200,
            content={"code": 403, "message": "forbidden"},
        )

    middleware = LogMiddleware(app=lambda scope, receive, send: None)
    await middleware.dispatch(request, call_next)

    logged_data = saved_log.await_args.args[1]
    assert logged_data.status == "error"
    assert logged_data.error == "ForbiddenError"
