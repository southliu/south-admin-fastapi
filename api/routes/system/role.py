from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import require_permission
from models.base import format_datetime
from schemas.response import ResponseModel
from schemas.role import (
    AuthorizeRoleRequest,
    CreateRoleRequest,
    UpdateRoleRequest,
)
from services.system.role import (
    create_role,
    delete_role,
    get_role_authorize,
    get_role_by_id,
    get_role_list,
    get_role_page,
    save_role_authorize,
    update_role,
)

router = APIRouter(prefix="/role", tags=["角色"])


@router.get("/page", response_model=ResponseModel[dict[str, object]])
async def get_role_page_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    name: str | None = Query(default=None, max_length=50),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/index")),
):
    """获取角色分页列表"""
    result = await get_role_page(db, page, page_size, name)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel[dict[str, object]])
async def get_role_detail(
    id: int = Query(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/view")),
):
    """获取角色详情"""
    role = await get_role_by_id(db, id)
    if not role:
        raise HTTPException(status_code=200, detail="角色不存在")

    menu_ids = [menu.id for menu in role.menus]

    return ResponseModel(
        code=200,
        message="获取成功",
        data={
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "createdAt": format_datetime(role.create_at),
            "updatedAt": format_datetime(role.update_at),
            "authorize": menu_ids,
        },
    )


@router.post("/create", response_model=ResponseModel[dict[str, object]])
async def create_role_handler(
    req: CreateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/create")),
):
    """创建角色"""
    try:
        role = await create_role(db, req)
        return ResponseModel(
            code=200,
            message="创建成功",
            data={
                "id": role.id,
                "name": role.name,
                "description": role.description,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.put(
    "/update/{role_id}",
    response_model=ResponseModel[dict[str, object]],
)
async def update_role_handler(
    role_id: PositiveInt,
    req: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/update")),
):
    """更新角色"""
    try:
        role = await update_role(db, role_id, req)
        return ResponseModel(
            code=200,
            message="更新成功",
            data={
                "id": role.id,
                "name": role.name,
                "description": role.description,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.delete("/{role_id}", response_model=ResponseModel[None])
async def delete_role_handler(
    role_id: PositiveInt,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/delete")),
):
    """删除角色"""
    try:
        await delete_role(db, role_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.get("/list", response_model=ResponseModel[list[dict[str, object]]])
async def get_role_list_handler(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/index")),
):
    """获取角色列表"""
    roles = await get_role_list(db)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
            }
            for role in roles
        ],
    )


@router.get(
    "/authorize",
    response_model=ResponseModel[dict[str, object]],
)
async def get_role_authorize_handler(
    role_id: int = Query(alias="roleId", gt=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/view")),
):
    """获取角色授权信息"""
    try:
        data = await get_role_authorize(db, role_id)
        return ResponseModel(code=200, message="获取成功", data=data)
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.post("/authorize", response_model=ResponseModel[None])
async def save_role_authorize_handler(
    req: AuthorizeRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/role/update")),
):
    """保存角色授权"""
    try:
        await save_role_authorize(db, req.role_id, req.menu_ids)
        return ResponseModel(code=200, message="保存成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc
