import unittest
from datetime import datetime

from models.system.menu import SysMenu
from models.system.permission import SysPermission
from services.system.menu import build_menu_tree
from services.system.role import _build_authorize_tree


class MenuTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        timestamp = datetime(2026, 1, 2, 3, 4, 5)
        self.menus = [
            SysMenu(
                id=menu_id,
                parent_id=parent_id,
                type=menu_type,
                label=f"菜单{menu_id}",
                label_en=f"Menu {menu_id}",
                router=f"/menu/{menu_id}",
                icon=None,
                order=0,
                state=1,
                permission_id=None,
                permission=None,
                create_at=timestamp,
                update_at=timestamp,
            )
            for menu_id, parent_id, menu_type in (
                (3, 2, 3),
                (2, 1, 2),
                (1, None, 1),
                (4, None, 1),
                (5, None, 2),
                (6, 999, 2),
            )
        ]

    def test_navigation_preserves_payload_order_and_hides_buttons(
        self,
    ) -> None:
        permission = SysPermission(id=10, name="/menu/view")
        self.menus[1].permission = permission
        self.menus[1].permission_id = permission.id

        tree = build_menu_tree(self.menus, None, allowed_ids={2})

        self.assertEqual([node["id"] for node in tree], [1, 4])
        self.assertEqual(
            tree[0]["children"],
            [
                {
                    "id": 2,
                    "label": "菜单2",
                    "labelEn": "Menu 2",
                    "title": "菜单2",
                    "titleEn": "Menu 2",
                    "key": "/menu/2",
                    "value": "2",
                    "icon": None,
                    "type": 2,
                    "router": "/menu/2",
                    "rule": "/menu/view",
                    "order": 0,
                    "state": 1,
                    "parentId": 1,
                    "permissionId": 10,
                    "createdAt": "2026-01-02 03:04:05",
                    "updatedAt": "2026-01-02 03:04:05",
                },
            ],
        )

    def test_management_includes_buttons_and_excludes_orphans(self) -> None:
        tree = build_menu_tree(self.menus, None, include_button=True)
        self.assertEqual([node["id"] for node in tree], [1, 4, 5])
        button = tree[0]["children"][0]["children"][0]
        self.assertEqual((button["id"], button["type"]), (3, 3))
        self.assertNotIn("children", button)

    def test_empty_permissions_keep_only_navigation_directories(self) -> None:
        tree = build_menu_tree(self.menus, None, allowed_ids=set())
        self.assertEqual([node["id"] for node in tree], [1, 4])
        self.assertTrue(all("children" not in node for node in tree))
        self.assertEqual(_build_authorize_tree(self.menus, None, set()), [])

    def test_authorized_button_keeps_ancestors(self) -> None:
        tree = _build_authorize_tree(self.menus, None, {3})
        self.assertEqual([node["key"] for node in tree], ["1"])
        page = tree[0]["children"][0]
        self.assertEqual(page["key"], "2")
        self.assertEqual(
            page["children"],
            [
                {
                    "title": "菜单3",
                    "value": "3",
                    "key": "3",
                    "type": 3,
                    "icon": None,
                },
            ],
        )

    def test_subtrees_and_empty_input(self) -> None:
        self.assertEqual(build_menu_tree([], None), [])
        self.assertEqual(_build_authorize_tree([], None, set()), [])
        tree = build_menu_tree(self.menus, 1, include_button=True)
        self.assertEqual([node["id"] for node in tree], [2])
        self.assertEqual(tree[0]["children"][0]["id"], 3)
        self.assertEqual(
            _build_authorize_tree(self.menus, 1, {2})[0]["key"], "2"
        )


if __name__ == "__main__":
    unittest.main()
