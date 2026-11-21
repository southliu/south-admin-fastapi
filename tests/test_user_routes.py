from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.routes.system import user as user_routes


async def test_user_detail_serializes_loaded_role_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    user = SimpleNamespace(
        id=1,
        username="user",
        name=None,
        email=None,
        phone=None,
        status=1,
        roles=[SimpleNamespace(id=2, name="editor")],
        create_at=now,
        update_at=now,
    )
    monkeypatch.setattr(
        user_routes,
        "get_user_by_id",
        AsyncMock(return_value=user),
    )

    response = await user_routes.get_user_detail(
        id=1,
        db=object(),
        current_user=SimpleNamespace(id=9),
    )

    assert response.data["roleIds"] == [2]
