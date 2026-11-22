import unittest
from unittest.mock import AsyncMock, patch

import main
from services.system.role import _parse_role_ids, get_role_authorize
from services.system.user import batch_delete_user


class FrontendContractTests(unittest.IsolatedAsyncioTestCase):
    def test_frontend_role_id_list(self) -> None:
        self.assertEqual(_parse_role_ids("1"), [1])
        self.assertEqual(_parse_role_ids("1, 2,1"), [1, 2])
        for value in ("", "1,,2", "abc", "0", "-1", "2147483648"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _parse_role_ids(value)

    def test_user_search_and_batch_delete_are_exposed(self) -> None:
        paths = main.app.openapi()["paths"]
        names = {
            item["name"]
            for item in paths["/system/user/page"]["get"]["parameters"]
        }
        self.assertTrue({"username", "email", "phone", "pageSize"} <= names)
        self.assertIn("post", paths["/system/user/batchDelete"])

    async def test_empty_batch_does_not_write(self) -> None:
        db = AsyncMock()
        with self.assertRaisesRegex(ValueError, "请选择"):
            await batch_delete_user(db, [], 1)
        db.execute.assert_not_awaited()
        db.flush.assert_not_awaited()

    async def test_protected_account_rejects_entire_batch(self) -> None:
        db = AsyncMock()
        db.scalar.return_value = 2
        with (
            patch(
                "services.system.user.is_admin",
                new=AsyncMock(return_value=False),
            ),
            self.assertRaisesRegex(ValueError, "管理员"),
        ):
            await batch_delete_user(db, [1, 2], 3)
        db.execute.assert_not_awaited()
        db.flush.assert_not_awaited()

    async def test_foreign_role_cannot_supply_authorization_options(
        self,
    ) -> None:
        db = AsyncMock()
        db.scalars.return_value = [1]
        with (
            patch(
                "services.system.role.is_admin",
                new=AsyncMock(return_value=False),
            ),
            self.assertRaisesRegex(ValueError, "没有访问权限"),
        ):
            await get_role_authorize(db, "1,2", 3)
        db.scalars.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
