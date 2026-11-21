from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from models.system.user import SysUser
from services.system.user import (
    get_user_identity_by_id,
    get_user_permission_names,
    user_has_role,
)
from utils.security import decode_access_token

security = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """认证失败异常"""


class ForbiddenError(Exception):
    """权限不足异常"""


async def auth_error_handler(request: Request, exc: AuthError):
    """认证失败异常处理"""
    request.state.operation_error = type(exc).__name__
    return JSONResponse(
        status_code=200,
        content={"code": 401, "data": "", "message": "无效权限访问"},
    )


async def forbidden_error_handler(
    request: Request,
    exc: ForbiddenError,
) -> JSONResponse:
    request.state.operation_error = type(exc).__name__
    return JSONResponse(
        status_code=200,
        content={"code": 403, "data": "", "message": "无权执行此操作"},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> SysUser:
    """获取当前用户"""
    if not credentials:
        raise AuthError()

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise AuthError()

    try:
        user_id = int(payload["sub"])
        token_version = int(payload.get("ver", 0))
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthError() from exc

    user = await get_user_identity_by_id(db, user_id)
    if user is None or user.status != 1 or user.token_version != token_version:
        raise AuthError()

    request.state.current_user = user
    request.state.current_username = user.username
    return user


def require_permission(permission: str) -> Callable[..., object]:
    async def dependency(
        current_user: SysUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> SysUser:
        permissions = await get_user_permission_names(db, current_user.id)
        if permission not in permissions:
            raise ForbiddenError()
        return current_user

    return dependency


def require_role(role_name: str) -> Callable[..., object]:
    async def dependency(
        current_user: SysUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> SysUser:
        if not await user_has_role(db, current_user.id, role_name):
            raise ForbiddenError()
        return current_user

    return dependency
