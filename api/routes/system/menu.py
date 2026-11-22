from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import get_current_user, require_permission
from models.system.user import SysUser
from schemas.menu import (
    BatchDeleteRequest,
    ChangeMenuStateRequest,
    CreateMenuRequest,
    UpdateMenuRequest,
)
from schemas.response import ResponseModel
from services.system.menu import (
    batch_delete_menu,
    change_menu_state,
    create_menu,
    delete_menu,
    get_menu_detail,
    get_menu_list,
    get_menu_page,
    update_menu,
)

router = APIRouter(prefix="/menu", tags=["菜单"])


@router.get("/list", response_model=ResponseModel)
async def get_menu_list_handlerget_menu_list_handler(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(get_current_user),
) -> ResponseModel:
    """获取用户菜单列表"""
    menus = await get_menu_list(db, current_user.id)
    return ResponseModel(code=200, message="获取成功", data=menus)


@router.get("/page", response_model=ResponseModel)
async def get_menu_page_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=200),
    label: str | None = None,
    label_en: str | None = Query(default=None, alias="labelEn"),
    state: int | None = None,
    rule: str | None = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission(
            "/authority/menu/index",
            "/authority/menu",
            "/authority/menu/create",
            "/authority/menu/update",
            "/authority/role/create",
            "/authority/role/update",
        )
    ),
) -> ResponseModel:
    """获取菜单分页列表"""
    result = await get_menu_page(
        db, page, page_size, label, label_en, state, rule
    )
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel)
async def get_menu_detail_handler(
    id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission(
            "/authority/menu/view", "/authority/menu", "/authority/menu/update"
        )
    ),
) -> ResponseModel:
    """获取菜单详情"""
    try:
        menu = await get_menu_detail(db, id)
        return ResponseModel(code=200, message="获取成功", data=menu)
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.post("/create", response_model=ResponseModel)
async def create_menu_handler(
    req: CreateMenuRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/menu/create")
    ),
) -> ResponseModel:
    """创建菜单"""
    try:
        menu = await create_menu(db, req, current_user.id)
        return ResponseModel(
            code=200,
            message="创建成功",
            data={
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
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.put("/update/{menu_id}", response_model=ResponseModel)
async def update_menu_handler(
    menu_id: int,
    req: UpdateMenuRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/menu/update")
    ),
) -> ResponseModel:
    """更新菜单"""
    try:
        menu = await update_menu(db, menu_id, req, current_user.id)
        return ResponseModel(
            code=200,
            message="更新成功",
            data={
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
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.delete("/{menu_id}", response_model=ResponseModel)
async def delete_menu_handler(
    menu_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/menu/delete")
    ),
) -> ResponseModel:
    """删除菜单"""
    try:
        await delete_menu(db, menu_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.post("/batchDelete", response_model=ResponseModel)
async def batch_delete_menu_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/menu/delete")
    ),
) -> ResponseModel:
    """批量删除菜单"""
    if not req.ids:
        raise HTTPException(status_code=200, detail="请选择要删除的菜单")

    try:
        await batch_delete_menu(db, req.ids)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.put("/changeState", response_model=ResponseModel)
async def change_menu_state_handler(
    req: ChangeMenuStateRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/menu/update")
    ),
) -> ResponseModel:
    """修改菜单状态"""
    try:
        await change_menu_state(db, req)
        return ResponseModel(code=200, message="修改成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e
