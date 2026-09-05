from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from services.system.menu import (
    get_menu_list,
    get_menu_page,
    get_menu_detail,
    create_menu,
    update_menu,
    delete_menu,
    batch_delete_menu,
    change_menu_state,
)
from schemas.response import ResponseModel
from schemas.menu import (
    CreateMenuRequest,
    UpdateMenuRequest,
    ChangeMenuStateRequest,
    BatchDeleteRequest,
)
from middleware.auth import get_current_user

router = APIRouter(prefix="/menu", tags=["菜单"])


@router.get("/list", response_model=ResponseModel)
async def get_menu_list_handlerget_menu_list_handler(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取用户菜单列表"""
    menus = await get_menu_list(db, current_user.id)
    return ResponseModel(code=200, message="获取成功", data=menus)


@router.get("/page", response_model=ResponseModel)
async def get_menu_page_list(
    page: int = 1,
    page_size: int = Query(default=10, alias="pageSize"),
    label: Optional[str] = None,
    labelEn: Optional[str] = None,
    state: Optional[int] = None,
    rule: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取菜单分页列表"""
    result = await get_menu_page(db, page, page_size, label, labelEn, state, rule)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel)
async def get_menu_detail_handler(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取菜单详情"""
    try:
        menu = await get_menu_detail(db, id)
        return ResponseModel(code=200, message="获取成功", data=menu)
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.post("/create", response_model=ResponseModel)
async def create_menu_handler(
    req: CreateMenuRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """创建菜单"""
    try:
        menu = await create_menu(db, req, current_user.id)
        return ResponseModel(code=200, message="创建成功", data={
            "id": menu.id,
            "label": menu.label,
            "labelEn": menu.label_en,
            "type": menu.type,
            "icon": menu.icon,
            "router": menu.router,
            "rule": menu.permission.name if menu.permission else None,
            "order": menu.order,
            "state": menu.state,
            "parentId": menu.parent_id,
        })
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.put("/update/{menu_id}", response_model=ResponseModel)
async def update_menu_handler(
    menu_id: int,
    req: UpdateMenuRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """更新菜单"""
    try:
        menu = await update_menu(db, menu_id, req)
        return ResponseModel(code=200, message="更新成功", data={
            "id": menu.id,
            "label": menu.label,
            "labelEn": menu.label_en,
            "type": menu.type,
            "icon": menu.icon,
            "router": menu.router,
            "rule": menu.permission.name if menu.permission else None,
            "order": menu.order,
            "state": menu.state,
            "parentId": menu.parent_id,
        })
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.delete("/{menu_id}", response_model=ResponseModel)
async def delete_menu_handler(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """删除菜单"""
    try:
        await delete_menu(db, menu_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.post("/batchDelete", response_model=ResponseModel)
async def batch_delete_menu_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """批量删除菜单"""
    if not req.ids:
        raise HTTPException(status_code=200, detail="请选择要删除的菜单")

    try:
        await batch_delete_menu(db, req.ids)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.put("/changeState", response_model=ResponseModel)
async def change_menu_state_handler(
    req: ChangeMenuStateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """修改菜单状态"""
    try:
        await change_menu_state(db, req)
        return ResponseModel(code=200, message="修改成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))
