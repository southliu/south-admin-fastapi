from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from services.system.permission import (
    get_permission_page,
    get_permission_list,
    get_permission_by_id,
    create_permission,
    update_permission,
    delete_permission,
)
from schemas.response import ResponseModel
from schemas.permission import CreatePermissionRequest, UpdatePermissionRequest
from middleware.auth import get_current_user
from models.base import format_datetime

router = APIRouter(prefix="/permission", tags=["权限"])


@router.get("/page", response_model=ResponseModel)
async def get_permission_page_list(
    page: int = 1,
    page_size: int = Query(default=10, alias="pageSize"),
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取权限分页列表"""
    result = await get_permission_page(db, page, page_size, name)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel)
async def get_permission_detail(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
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
        }
    )


@router.post("/create", response_model=ResponseModel)
async def create_permission_handler(
    req: CreatePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """创建权限"""
    try:
        permission = await create_permission(db, req)
        return ResponseModel(code=200, message="创建成功", data={
            "id": permission.id,
            "name": permission.name,
            "description": permission.description,
        })
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.put("/update/{permission_id}", response_model=ResponseModel)
async def update_permission_handler(
    permission_id: int,
    req: UpdatePermissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """更新权限"""
    try:
        permission = await update_permission(db, permission_id, req)
        return ResponseModel(code=200, message="更新成功", data={
            "id": permission.id,
            "name": permission.name,
            "description": permission.description,
        })
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.delete("/{permission_id}", response_model=ResponseModel)
async def delete_permission_handler(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """删除权限"""
    try:
        await delete_permission(db, permission_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.get("/list", response_model=ResponseModel)
async def get_permission_list_handler(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
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
        ]
    )
