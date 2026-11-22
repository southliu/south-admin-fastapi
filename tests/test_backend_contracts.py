import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

from middleware.auth import (
    AuthError,
    PermissionDeniedError,
    get_current_user,
    require_permission,
)
from middleware.log import LogMiddleware
from schemas.log import CreateLogRequest
from services.system.access import validate_role_grant, validate_user_grant
from services.system.log import create_log
from utils.audit import MAX_AUDIT_BYTES, sanitize_params, sanitize_url
from utils.security import hash_password, verify_password


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_user_and_invalid_subject_are_rejected(
        self,
    ) -> None:
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test"
        )
        request = Request({"type": "http", "state": {}, "headers": []})
        with (
            patch(
                "middleware.auth.decode_access_token",
                return_value={"sub": "1"},
            ),
            patch(
                "middleware.auth.get_user_identity",
                new=AsyncMock(return_value=SimpleNamespace(id=1, status=0)),
            ),
            self.assertRaises(AuthError),
        ):
            await get_current_user(request, credentials, AsyncMock())
        for subject in (None, "invalid", "9" * 5000, "-1", "0"):
            with (
                self.subTest(subject_length=len(str(subject))),
                patch(
                    "middleware.auth.decode_access_token",
                    return_value={"sub": subject},
                ),
                self.assertRaises(AuthError),
            ):
                await get_current_user(request, credentials, AsyncMock())

    async def test_permission_alias_and_admin_bypass(self) -> None:
        check = require_permission("/authority/user/view")
        for admin, permissions, allowed in (
            (False, set(), False),
            (False, {"/authority/user/create"}, False),
            (False, {"/authority/user/view"}, True),
            (False, {"/system/user/detail"}, True),
            (True, set(), True),
        ):
            request = Request({"type": "http", "state": {}, "headers": []})
            user = SimpleNamespace(id=1)
            with patch(
                "middleware.auth.get_user_access",
                new=AsyncMock(return_value=(admin, permissions)),
            ):
                if allowed:
                    self.assertIs(
                        await check(request, user, AsyncMock()), user
                    )
                else:
                    with self.assertRaises(PermissionDeniedError):
                        await check(request, user, AsyncMock())

    async def test_grants_cannot_exceed_held_roles_or_menus(self) -> None:
        db = AsyncMock()
        db.scalars.return_value = [1]
        with patch(
            "services.system.access.is_admin",
            new=AsyncMock(return_value=False),
        ):
            await validate_user_grant(db, 1, [1])
            with self.assertRaises(ValueError):
                await validate_user_grant(db, 1, [2])
            with self.assertRaises(ValueError):
                await validate_role_grant(db, 1, "admin", [])
            with self.assertRaises(ValueError):
                await validate_role_grant(db, 1, "editor", [2])

    async def test_password_hashing_preserves_event_loop(self) -> None:
        task = asyncio.create_task(hash_password("test-password"))
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        hashed = await task
        self.assertTrue(await verify_password("test-password", hashed))
        self.assertFalse(await verify_password("wrong-password", hashed))
        self.assertFalse(await verify_password("x" * 73, hashed))
        with self.assertRaisesRegex(ValueError, "72"):
            await hash_password("x" * 73)


class AuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_log_storage_redacts_nested_secrets_and_query(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        log = await create_log(
            db,
            CreateLogRequest(
                params=json.dumps(
                    {
                        "password": "never-store",
                        "nested": [{"accessToken": "secret"}],
                        "label": "菜单",
                        "params": json.dumps({"password": "never-store"}),
                        "url": "https://example.com/path?token=secret",
                        "error": "token=secret",
                    }
                ),
                url="http://user:secret@example.com/path?token=secret",
            ),
        )
        self.assertNotIn("never-store", log.params)
        self.assertNotIn("secret", log.params)
        self.assertIn("菜单", log.params)
        self.assertEqual(log.url, "http://example.com/path")
        db.commit.assert_not_awaited()
        self.assertNotIn("secret", sanitize_params("not-json secret"))
        self.assertLess(len(sanitize_params("x" * (MAX_AUDIT_BYTES + 1))), 100)
        self.assertEqual(sanitize_url("/path?password=secret"), "/path")

    async def test_http_200_business_failure_is_logged_as_error(self) -> None:
        async def app(scope, receive, send):
            await receive()
            scope.setdefault("state", {})["audit_username"] = "tester"
            await send(
                {"type": "http.response.start", "status": 200, "headers": []}
            )
            await send({"type": "http.response.body", "body": b'{"code":500}'})

        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=AsyncMock())
        context.__aexit__ = AsyncMock(return_value=False)
        factory = MagicMock()
        factory.begin.return_value = context
        store = AsyncMock()
        with (
            patch("middleware.log.AsyncSessionLocal", factory),
            patch("middleware.log.create_log", store),
        ):
            await LogMiddleware(app)(
                {
                    "type": "http",
                    "method": "POST",
                    "scheme": "http",
                    "path": "/test",
                    "query_string": b"",
                    "headers": [],
                    "server": ("localhost", 80),
                    "state": {},
                },
                AsyncMock(
                    return_value={"type": "http.request", "body": b"{}"}
                ),
                AsyncMock(),
            )
        entry = store.await_args.args[1]
        self.assertEqual(entry.status, "error")
        self.assertEqual(entry.type, 0)
        self.assertEqual(entry.username, "tester")


if __name__ == "__main__":
    unittest.main()
