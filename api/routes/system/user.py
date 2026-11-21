from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import get_current_user, require_permission
from models.base import format_datetime
from schemas.response import ResponseModel
from schemas.user import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    RefreshPermissionsResponse,
    UpdatePasswordRequest,
    UpdateUserRequest,
)
from services.system.user import (
    create_user,
    delete_user,
    get_user_by_id,
    get_user_by_username,
    get_user_list,
    get_user_page,
    get_user_permission_names,
    get_user_role_ids,
    revoke_user_tokens,
    update_user,
    update_user_password,
)
from utils.security import create_access_token, verify_password_async

router = APIRouter(prefix="/user", tags=["用户"])


@router.post("/login", response_model=ResponseModel[LoginResponse])
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    user = await get_user_by_username(db, req.username)
    if not user:
        raise HTTPException(status_code=200, detail="用户名或密码错误")

    if not await verify_password_async(req.password, user.password):
        raise HTTPException(status_code=200, detail="用户名或密码错误")

    if user.status != 1:
        raise HTTPException(status_code=200, detail="用户已被禁用")

    # 生成 JWT
    token = create_access_token(
        data={"sub": str(user.id), "ver": user.token_version}
    )

    # 获取用户权限
    permissions = sorted(await get_user_permission_names(db, user.id))
    roles = await get_user_role_ids(db, user.id)

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


@router.post("/logout", response_model=ResponseModel[None])
async def logout(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """退出登录"""
    await revoke_user_tokens(db, current_user.id)
    return ResponseModel[None](code=200, message="退出登录成功")


@router.get(
    "/refreshPermissions",
    response_model=ResponseModel[RefreshPermissionsResponse],
)
async def refresh_permissions(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """刷新用户权限"""
    user = current_user
    permissions = sorted(await get_user_permission_names(db, user.id))
    roles = await get_user_role_ids(db, user.id)

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


@router.get("/page", response_model=ResponseModel[dict[str, object]])
async def get_user_page_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    username: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/user/index")),
):
    """获取用户分页列表"""
    result = await get_user_page(db, page, page_size, username)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel[dict[str, object]])
async def get_user_detail(
    id: PositiveInt,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/user/view")),
):
    """获取用户详情"""
    user = await get_user_by_id(db, id)
    if not user:
        raise HTTPException(status_code=200, detail="用户不存在")

    roles = [role.id for role in user.roles]

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


@router.post("/create", response_model=ResponseModel[dict[str, object]])
async def create_user_handler(
    req: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/user/create")),
):
    """创建用户"""
    try:
        user = await create_user(db, req)
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
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.put(
    "/update/{user_id}",
    response_model=ResponseModel[dict[str, object]],
)
async def update_user_handler(
    user_id: PositiveInt,
    req: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/user/update")),
):
    """更新用户"""
    if user_id == current_user.id and req.status == 0:
        raise HTTPException(status_code=200, detail="不能禁用当前登录用户")
    try:
        user = await update_user(db, user_id, req)
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
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.delete("/{user_id}", response_model=ResponseModel[None])
async def delete_user_handler(
    user_id: PositiveInt,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/user/delete")),
):
    """删除用户"""
    if user_id == current_user.id:
        raise HTTPException(status_code=200, detail="不能删除当前登录用户")
    try:
        await delete_user(db, user_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.get("/list", response_model=ResponseModel[list[dict[str, object]]])
async def get_user_list_handler(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/user/index")),
):
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


@router.post("/updatePassword", response_model=ResponseModel[None])
async def update_password_handler(
    req: UpdatePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新密码"""
    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=200,
            detail="两次输入的新密码不一致",
        )

    try:
        await update_user_password(
            db, current_user.id, req.old_password, req.new_password
        )
        return ResponseModel(code=200, message="更新成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc
