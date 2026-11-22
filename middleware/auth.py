from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from models.system.user import SysUser
from services.system.user import get_user_access, get_user_identity
from utils.security import decode_access_token

security = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """认证失败。"""


class PermissionDeniedError(Exception):
    """已登录用户缺少操作权限。"""


async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    request.state.audit_code = 401
    return JSONResponse(
        status_code=200,
        content={"code": 401, "data": "", "message": "无效权限访问"},
    )


async def permission_error_handler(
    request: Request, exc: PermissionDeniedError
) -> JSONResponse:
    request.state.audit_code = 500
    return JSONResponse(
        status_code=200,
        content={"code": 500, "data": "", "message": "没有操作权限"},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> SysUser:
    if credentials is None:
        raise AuthError()
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise AuthError()
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdecimal():
        raise AuthError()
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise AuthError() from exc
    if not 0 < user_id <= 2**31 - 1:
        raise AuthError()
    user = await get_user_identity(db, user_id)
    if user is None or user.status != 1:
        raise AuthError()
    request.state.user = user
    request.state.audit_username = user.username
    return user


def require_permission(
    *permissions: str,
) -> Callable[..., Coroutine[Any, Any, SysUser]]:
    accepted = set(permissions)
    for permission in permissions:
        accepted.add(permission.replace("/authority/", "/system/", 1))
        if permission.endswith("/view"):
            accepted.add(permission.removesuffix("/view") + "/detail")
            accepted.add(
                permission.replace("/authority/", "/system/", 1).removesuffix(
                    "/view"
                )
                + "/detail"
            )

    async def check(
        request: Request,
        user: SysUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db, scope="function"),
    ) -> SysUser:
        access = getattr(request.state, "access", None)
        if access is None:
            access = await get_user_access(db, user.id)
            request.state.access = access
        is_admin, granted = access
        if not is_admin and not accepted.intersection(granted):
            raise PermissionDeniedError()
        return user

    return check


def get_user_permissions(user: SysUser) -> list[str]:
    return sorted(
        {
            menu.permission.name
            for role in user.roles
            if not role.is_deleted
            for menu in role.menus
            if not menu.is_deleted
            and menu.permission is not None
            and not menu.permission.is_deleted
        }
    )


def get_user_role_ids(user: SysUser) -> list[int]:
    return [role.id for role in user.roles if not role.is_deleted]


async def require_admin(
    user: SysUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> SysUser:
    from services.system.access import is_admin

    if not await is_admin(db, user.id):
        raise PermissionDeniedError()
    return user
