from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from models.system.menu import SysMenu
from services.system import role as role_service


def make_menu(
    menu_id: int,
    parent_id: int | None = None,
) -> SysMenu:
    now = datetime.now(UTC)
    return SysMenu(
        id=menu_id,
        label=f"menu-{menu_id}",
        label_en=f"menu-{menu_id}",
        type=2,
        order=menu_id,
        state=1,
        parent_id=parent_id,
        permission_id=None,
        is_deleted=0,
        create_at=now,
        update_at=now,
    )


def test_authorize_tree_contains_unassigned_menus() -> None:
    tree = role_service._build_authorize_tree(
        [make_menu(1), make_menu(2, parent_id=1)],
        None,
    )

    assert tree[0]["key"] == "1"
    assert tree[0]["children"][0]["key"] == "2"


async def test_admin_role_cannot_be_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        role_service,
        "get_role_by_id",
        AsyncMock(return_value=SimpleNamespace(name="admin")),
    )

    with pytest.raises(ValueError, match="不能删除"):
        await role_service.delete_role(AsyncMock(), 1)
