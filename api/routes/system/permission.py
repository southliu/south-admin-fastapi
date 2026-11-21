from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import require_role
from models.base import format_datetime
from schemas.permission import CreatePermissionRequest, UpdatePermissionRequest
from schemas.response import ResponseModel
from services.system.permission import (
    create_permission,
    delete_permission,
    get_permission_by_id,
    get_permission_list,
    get_permission_page,
    update_permission,
)

router = APIRouter(prefix="/permission", tags=["权限"])


@router.get("/page", response_model=ResponseModel[dict[str, object]])
async def get_permission_page_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    name: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """获取权限分页列表"""
    result = await get_permission_page(db, page, page_size, name)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel[dict[str, object]])
async def get_permission_detail(
    id: int = Query(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """获取权限详情"""
    permission = await get_permission_by_id(db, id)
    if not permission:
        raise HTTPException(status_code=200, detail="权限不存在")

    return ResponseModel(
        code=200,
        message="获取成功",
        data={
            "id": permission.id,
            "name": permission.name,
            "description": permission.description,
            "createdAt": format_datetime(permission.create_at),
            "updatedAt": format_datetime(permission.update_at),
        },
    )


@router.post("/create", response_model=ResponseModel[dict[str, object]])
async def create_permission_handler(
    req: CreatePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """创建权限"""
    try:
        permission = await create_permission(db, req)
        return ResponseModel(
            code=200,
            message="创建成功",
            data={
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.put(
    "/update/{permission_id}",
    response_model=ResponseModel[dict[str, object]],
)
async def update_permission_handler(
    permission_id: PositiveInt,
    req: UpdatePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """更新权限"""
    try:
        permission = await update_permission(db, permission_id, req)
        return ResponseModel(
            code=200,
            message="更新成功",
            data={
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.delete("/{permission_id}", response_model=ResponseModel[None])
async def delete_permission_handler(
    permission_id: PositiveInt,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """删除权限"""
    try:
        await delete_permission(db, permission_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.get("/list", response_model=ResponseModel[list[dict[str, object]]])
async def get_permission_list_handler(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """获取权限列表"""
    permissions = await get_permission_list(db)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[
            {
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
            }
            for permission in permissions
        ],
    )
