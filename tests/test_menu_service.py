from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from models.system.menu import SysMenu
from services.system.menu import (
    _collect_subtree_ids,
    build_menu_tree,
    get_menu_page,
)


def make_menu(
    menu_id: int,
    label: str,
    parent_id: int | None = None,
    menu_type: int = 2,
) -> SysMenu:
    now = datetime.now(UTC)
    return SysMenu(
        id=menu_id,
        label=label,
        label_en=label,
        type=menu_type,
        order=menu_id,
        state=1,
        parent_id=parent_id,
        permission_id=None,
        is_deleted=0,
        create_at=now,
        update_at=now,
    )


def test_collect_subtree_ids_includes_every_descendant() -> None:
    parents = {1: None, 2: 1, 3: 2, 4: None}

    assert _collect_subtree_ids(parents, {1}) == {1, 2, 3}


def test_user_tree_hides_empty_unauthorized_directories() -> None:
    directory = make_menu(1, "empty", menu_type=1)

    assert build_menu_tree([directory], None, allowed_ids={99}) == []


async def test_menu_page_paginates_root_nodes() -> None:
    first = make_menu(1, "first", menu_type=1)
    child = make_menu(2, "child", parent_id=1)
    second = make_menu(3, "second", menu_type=1)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [first, child, second]
    session = AsyncMock()
    session.execute.return_value = result

    page = await get_menu_page(session, page=2, page_size=1)

    assert page["total"] == 2
    assert page["totalPages"] == 2
    assert [item["id"] for item in page["items"]] == [3]
