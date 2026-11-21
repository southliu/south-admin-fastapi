from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from middleware import auth
from middleware.auth import AuthError, ForbiddenError
from utils.security import create_access_token


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("test", 50000),
        }
    )


@pytest.mark.parametrize(
    ("status", "user_version", "token_version"),
    [(0, 2, 2), (1, 3, 2)],
)
async def test_current_user_rejects_disabled_or_revoked_token(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    user_version: int,
    token_version: int,
) -> None:
    user = SimpleNamespace(
        id=1,
        status=status,
        token_version=user_version,
    )
    monkeypatch.setattr(
        auth,
        "get_user_identity_by_id",
        AsyncMock(return_value=user),
    )
    token = create_access_token({"sub": "1", "ver": token_version})
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with pytest.raises(AuthError):
        await auth.get_current_user(make_request(), credentials, object())


async def test_current_user_sets_request_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=1,
        username="user",
        status=1,
        token_version=4,
    )
    monkeypatch.setattr(
        auth,
        "get_user_identity_by_id",
        AsyncMock(return_value=user),
    )
    token = create_access_token({"sub": "1", "ver": 4})
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    request = make_request()

    result = await auth.get_current_user(request, credentials, object())

    assert result is user
    assert request.state.current_user is user
    assert request.state.current_username == "user"


async def test_permission_dependency_denies_missing_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=1)
    monkeypatch.setattr(
        auth,
        "get_user_permission_names",
        AsyncMock(return_value={"/dashboard"}),
    )
    dependency = auth.require_permission("/authority/user/index")

    with pytest.raises(ForbiddenError):
        await dependency(current_user=user, db=object())
