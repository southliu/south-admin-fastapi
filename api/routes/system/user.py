from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import (
    get_current_user,
    get_user_permissions,
    get_user_role_ids,
    require_permission,
)
from models.base import format_datetime
from models.system.user import SysUser
from schemas.menu import BatchDeleteRequest
from schemas.response import ResponseModel
from schemas.user import (
    CreateUserRequest,
    LoginRequest,
    UpdatePasswordRequest,
    UpdateUserRequest,
    UserPageQuery,
)
from services.system.user import (
    batch_delete_user,
    create_user,
    delete_user,
    get_user_by_id,
    get_user_by_username,
    get_user_list,
    get_user_page,
    update_user,
    update_user_password,
)
from utils.security import create_access_token, verify_password

router = APIRouter(prefix="/user", tags=["用户"])


@router.post("/login", response_model=ResponseModel)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db, scope="function"),
) -> ResponseModel:
    """用户登录"""
    user = await get_user_by_username(db, req.username)
    if not user:
        raise HTTPException(status_code=200, detail="用户名或密码错误")

    if not await verify_password(req.password, user.password):
        raise HTTPException(status_code=200, detail="用户名或密码错误")

    if user.status != 1:
        raise HTTPException(status_code=200, detail="用户已被禁用")

    request.state.audit_username = user.username
    # 生成 JWT
    token = create_access_token(data={"sub": str(user.id)})

    # 获取用户权限
    permissions = get_user_permissions(user)
    roles = get_user_role_ids(user)

    return ResponseModel(
        code=200,
        message="登录成功",
        data={
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "phone": user.phone,
                "email": user.email,
                "status": user.status,
                "roles": roles,
            },
            "roles": roles,
            "permissions": permissions,
        },
    )


@router.post("/logout", response_model=ResponseModel)
async def logout() -> ResponseModel:
    """退出登录"""
    return ResponseModel(code=200, message="退出登录成功")


@router.get("/refreshPermissions", response_model=ResponseModel)
async def refresh_permissions(
    current_user: SysUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> ResponseModel:
    """刷新用户权限"""
    user = await get_user_by_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=200, detail="用户不存在")

    permissions = get_user_permissions(user)
    roles = get_user_role_ids(user)

    return ResponseModel(
        code=200,
        message="获取成功",
        data={
            "user": {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "phone": user.phone,
                "email": user.email,
                "status": user.status,
                "roles": roles,
            },
            "permissions": permissions,
            "roles": roles,
        },
    )


@router.get("/page", response_model=ResponseModel)
async def get_user_page_list(
    query: Annotated[UserPageQuery, Query()],
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/user/index", "/authority/user")
    ),
) -> ResponseModel:
    """获取用户分页列表"""
    result = await get_user_page(db, query)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel)
async def get_user_detail(
    id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission(
            "/authority/user/view", "/authority/user", "/authority/user/update"
        )
    ),
) -> ResponseModel:
    """获取用户详情"""
    user = await get_user_by_id(db, id)
    if not user:
        raise HTTPException(status_code=200, detail="用户不存在")

    roles = get_user_role_ids(user)

    return ResponseModel(
        code=200,
        message="获取成功",
        data={
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "status": user.status,
            "roleIds": roles,
            "roles": [
                {"id": role.id, "name": role.name} for role in user.roles
            ],
            "createdAt": format_datetime(user.create_at),
            "updatedAt": format_datetime(user.update_at),
        },
    )


@router.post("/create", response_model=ResponseModel)
async def create_user_handler(
    req: CreateUserRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/user/create")
    ),
) -> ResponseModel:
    """创建用户"""
    try:
        user = await create_user(db, req, current_user.id)
        return ResponseModel(
            code=200,
            message="创建成功",
            data={
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "status": user.status,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.put("/update/{user_id}", response_model=ResponseModel)
async def update_user_handler(
    user_id: int,
    req: UpdateUserRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/user/update")
    ),
) -> ResponseModel:
    """更新用户"""
    try:
        user = await update_user(db, user_id, req, current_user.id)
        return ResponseModel(
            code=200,
            message="更新成功",
            data={
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "status": user.status,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user_handler(
    user_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/user/delete")
    ),
) -> ResponseModel:
    """删除用户"""
    try:
        await delete_user(db, user_id, current_user.id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.get("/list", response_model=ResponseModel)
async def get_user_list_handler(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/user/index", "/authority/user")
    ),
) -> ResponseModel:
    """获取用户列表"""
    users = await get_user_list(db)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
            }
            for user in users
        ],
    )


@router.post("/updatePassword", response_model=ResponseModel)
async def update_password_handler(
    req: UpdatePasswordRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(get_current_user),
) -> ResponseModel:
    """更新密码"""
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=200, detail="新旧密码不一致")

    try:
        await update_user_password(
            db, current_user.id, req.old_password, req.new_password
        )
        return ResponseModel(code=200, message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.post("/batchDelete", response_model=ResponseModel)
async def batch_delete_user_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/user/delete")
    ),
) -> ResponseModel:
    try:
        await batch_delete_user(db, req.ids, current_user.id)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc
