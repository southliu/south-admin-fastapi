from unittest.mock import AsyncMock, MagicMock

import pytest

from schemas.user import CreateUserRequest
from services.system import user as user_service


async def test_create_user_preserves_disabled_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    session.add = MagicMock()
    monkeypatch.setattr(
        user_service,
        "get_any_user_by_username",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        user_service,
        "hash_password_async",
        AsyncMock(return_value="hashed-password"),
    )
    monkeypatch.setattr(
        user_service,
        "update_user_roles",
        AsyncMock(),
    )

    result = await user_service.create_user(
        session,
        CreateUserRequest(
            username="disabled-user",
            password="safe-password",
            status=0,
        ),
    )

    assert result.status == 0
    session.flush.assert_awaited_once()
