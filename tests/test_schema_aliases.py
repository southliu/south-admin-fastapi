import unittest

from schemas.menu import CreateMenuRequest, UpdateMenuRequest
from schemas.response import PageData
from schemas.role import AuthorizeRoleRequest


class SchemaAliasTests(unittest.TestCase):
    def test_menu_accepts_both_field_names(self) -> None:
        for field_names in (
            {"labelEn": "Menu", "parentId": 7},
            {"label_en": "Menu", "parent_id": 7},
        ):
            with self.subTest(field_names=field_names):
                menu = CreateMenuRequest.model_validate(
                    {"label": "菜单", "type": 2, "state": 0, **field_names}
                )
                self.assertEqual(menu.label_en, "Menu")
                self.assertEqual(menu.parent_id, 7)
                self.assertEqual(menu.state, 0)

    def test_alias_takes_precedence(self) -> None:
        authorization = AuthorizeRoleRequest.model_validate(
            {"roleId": 1, "role_id": 2, "menuIds": []}
        )
        self.assertEqual(authorization.role_id, 1)
        self.assertEqual(authorization.menu_ids, [])

    def test_update_preserves_empty_fields_and_zero(self) -> None:
        menu = UpdateMenuRequest.model_validate(
            {"label": "菜单", "labelEn": "Menu", "rule": "", "state": 0}
        )
        self.assertEqual(menu.rule, "")
        self.assertEqual(menu.state, 0)
        self.assertIsNone(menu.icon)
        self.assertIsNone(menu.parent_id)

    def test_pagination_serialization_remains_camel_case(self) -> None:
        page = PageData(page_size=20, total_pages=3)
        self.assertEqual(
            page.model_dump(by_alias=True),
            {
                "items": [],
                "page": 1,
                "pageSize": 20,
                "total": 0,
                "totalPages": 3,
            },
        )


if __name__ == "__main__":
    unittest.main()
