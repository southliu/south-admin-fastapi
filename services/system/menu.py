from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.system.permission import get_permission_by_name
from models.system.menu import SysMenu
from models.system.permission import SysPermission
from models.system.user import user_role
from models.system.role import role_menu
from models.base import format_datetime
from schemas.menu import CreateMenuRequest, UpdateMenuRequest, ChangeMenuStateRequest

# 按钮动作标签映射
ACTION_LABELS = {
    "create": ("新增", "Create"),
    "update": ("修改", "Update"),
    "delete": ("删除", "Delete"),
    "detail": ("详情", "Detail"),
    "export": ("导出权限", "Export"),
    "status": ("状态权限", "Status"),
}


async def get_or_create_permission(db: AsyncSession, name: str, description: str) -> SysPermission:
    """获取或创建权限"""
    result = await db.execute(
        select(SysPermission).where(SysPermission.name == name)
    )
    permission = result.scalar_one_or_none()
    if permission:
        return permission

    permission = SysPermission(name=name, description=description)
    db.add(permission)
    await db.flush()
    await db.refresh(permission)
    return permission


async def get_menu_by_id(db: AsyncSession, menu_id: int) -> Optional[SysMenu]:
    """根据ID查询菜单"""
    result = await db.execute(
        select(SysMenu)
        .where(and_(SysMenu.id == menu_id, SysMenu.is_deleted == 0))
        .options(selectinload(SysMenu.permission))
        .options(selectinload(SysMenu.children))
    )
    return result.scalar_one_or_none()


async def get_menu_list(db: AsyncSession, user_id: int) -> List[dict]:
    """获取用户菜单列表"""
    from services.system.user import get_user_by_id

    user = await get_user_by_id(db, user_id)
    if not user:
        return []

    # 从角色关联的菜单中获取 permission_id
    permission_ids = set()
    for role in user.roles:
        for menu in role.menus:
            if menu.permission_id:
                permission_ids.add(menu.permission_id)

    if not permission_ids:
        return []

    # 查询有权限的菜单ID（排除按钮类型）
    permitted_result = await db.execute(
        select(SysMenu.id).where(and_(
            SysMenu.permission_id.in_(permission_ids),
            SysMenu.is_deleted == 0,
            SysMenu.type != 3
        ))
    )
    permitted_menu_ids = set(permitted_result.scalars().all())

    if not permitted_menu_ids:
        return []

    # 查询所有可见菜单（包含父级目录）
    result = await db.execute(
        select(SysMenu)
        .where(and_(SysMenu.is_deleted == 0, SysMenu.state == 1))
        .options(selectinload(SysMenu.permission))
        .order_by(SysMenu.order)
    )
    all_menus = result.scalars().all()

    # 构建树形结构（只保留用户有权限的分支）
    return build_menu_tree(all_menus, None, allowed_ids=permitted_menu_ids)


async def get_menu_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    label: Optional[str] = None,
    label_en: Optional[str] = None,
    state: Optional[int] = None,
    rule: Optional[str] = None
) -> dict:
    """获取菜单分页列表（树形结构）"""
    query = select(SysMenu).where(SysMenu.is_deleted == 0)

    if label:
        query = query.where(SysMenu.label.like(f"%{label}%"))
    if label_en:
        query = query.where(SysMenu.label_en.like(f"%{label_en}%"))
    if state is not None:
        query = query.where(SysMenu.state == state)
    if rule:
        query = query.join(SysPermission, SysMenu.permission_id == SysPermission.id).where(SysPermission.name.like(f"%{rule}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询所有菜单并构建树形结构
    query = query.options(selectinload(SysMenu.permission)).order_by(SysMenu.order)
    result = await db.execute(query)
    menus = result.scalars().all()

    # 构建树形结构（包含所有类型）
    items = build_menu_tree(menus, None, include_button=True)

    total_pages = total // page_size
    if total % page_size > 0:
        total_pages += 1

    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": total_pages,
    }


async def get_menu_detail(db: AsyncSession, menu_id: int) -> dict:
    """获取菜单详情"""
    menu = await get_menu_by_id(db, menu_id)
    if not menu:
        raise ValueError("菜单不存在")

    return {
        "id": menu.id,
        "label": menu.label,
        "labelEn": menu.label_en,
        "icon": menu.icon,
        "type": menu.type,
        "router": menu.router,
        "rule": menu.permission.name if menu.permission else None,
        "order": menu.order,
        "state": menu.state,
        "parentId": menu.parent_id,
        "permissionId": menu.permission_id,
        "createdAt": format_datetime(menu.create_at),
        "updatedAt": format_datetime(menu.update_at),
    }


async def create_menu(db: AsyncSession, data: CreateMenuRequest, user_id: int) -> SysMenu:
    """创建菜单"""
    permission_id = None

    # 如果有 rule，自动创建权限记录
    if data.rule:
        permission = await get_or_create_permission(db, data.rule, data.label)
        permission_id = permission.id

    menu = SysMenu(
        label=data.label,
        label_en=data.label_en,
        type=data.type,
        icon=data.icon,
        router=data.router,
        order=data.order,
        state=data.state,
        parent_id=data.parent_id,
        permission_id=permission_id,
    )

    db.add(menu)
    await db.flush()
    await db.refresh(menu)

    # 关联当前用户的角色与新菜单
    result = await db.execute(
        select(user_role.c.role_id).where(user_role.c.user_id == user_id)
    )
    role_ids = result.scalars().all()
    if role_ids:
        for role_id in role_ids:
            await db.execute(
                role_menu.insert().values(role_id=role_id, menu_id=menu.id)
            )

    # 根据 actions 创建按钮子菜单
    if data.actions and data.rule:
        for action in data.actions:
            labels = ACTION_LABELS.get(action)
            if not labels:
                continue

            button_rule = f"{data.rule}/{action}"
            button_permission = await get_or_create_permission(db, button_rule, labels[0])

            button_menu = SysMenu(
                label=labels[0],
                label_en=labels[1],
                type=3,
                router="",
                order=0,
                state=1,
                parent_id=menu.id,
                permission_id=button_permission.id,
            )
            db.add(button_menu)
            await db.flush()
            await db.refresh(button_menu)

            # 关联按钮菜单到用户的角色
            if role_ids:
                for role_id in role_ids:
                    await db.execute(
                        role_menu.insert().values(role_id=role_id, menu_id=button_menu.id)
                    )

    await db.commit()
    return menu


async def update_menu(db: AsyncSession, menu_id: int, data: UpdateMenuRequest) -> SysMenu:
    """更新菜单"""
    menu = await get_menu_by_id(db, menu_id)
    if not menu:
        raise ValueError("菜单不存在")

    menu.label = data.label
    menu.label_en = data.label_en

    # 可空字段：直接赋值，前端不传即为 None → 清空
    menu.icon = data.icon
    menu.router = data.router
    menu.parent_id = data.parent_id

    # 非空字段：仅在显式传入时才更新
    if data.type is not None:
        menu.type = data.type
    if data.order is not None:
        menu.order = data.order
    if data.state is not None:
        menu.state = data.state

    # 同步权限：非空 → 复用/新建或重命名；空值（不传/传空）→ 解除关联，权限记录保留由权限管理维护
    if data.rule:
        if menu.permission:
            if menu.permission.name != data.rule:
                existing = await get_permission_by_name(db, data.rule)
                if existing and existing.id != menu.permission_id:
                    raise ValueError("权限名已存在")
                menu.permission.name = data.rule
        else:
            menu.permission = await get_or_create_permission(db, data.rule, data.label)
    elif menu.permission:
        menu.permission = None

    await db.commit()
    await db.refresh(menu)
    return menu


async def delete_menu(db: AsyncSession, menu_id: int) -> None:
    """删除菜单"""
    menu = await get_menu_by_id(db, menu_id)
    if not menu:
        raise ValueError("菜单不存在")

    from datetime import datetime
    from models.system.role import role_menu

    # 先删除角色-菜单关联关系
    await db.execute(
        role_menu.delete().where(role_menu.c.menu_id == menu_id)
    )

    menu.is_deleted = 1
    menu.deleted_at = datetime.now()
    await db.commit()


async def batch_delete_menu(db: AsyncSession, menu_ids: List[int]) -> None:
    """批量删除菜单"""
    from datetime import datetime
    from models.system.role import role_menu

    # 先删除角色-菜单关联关系
    await db.execute(
        role_menu.delete().where(role_menu.c.menu_id.in_(menu_ids))
    )

    # 软删除菜单
    for menu_id in menu_ids:
        menu = await get_menu_by_id(db, menu_id)
        if menu:
            menu.is_deleted = 1
            menu.deleted_at = datetime.now()

    await db.commit()


async def change_menu_state(db: AsyncSession, data: ChangeMenuStateRequest) -> None:
    """修改菜单状态"""
    menu = await get_menu_by_id(db, data.id)
    if not menu:
        raise ValueError("菜单不存在")

    menu.state = data.state
    await db.commit()


def build_menu_tree(menus: List[SysMenu], parent_id: Optional[int], include_button: bool = False, allowed_ids: Optional[set] = None) -> List[dict]:
    """构建菜单树形结构"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id and (include_button or menu.type != 3):
            children = build_menu_tree(menus, menu.id, include_button, allowed_ids)
            # 如果有权限过滤，只保留有权限的菜单或包含有权限子菜单的父级，目录类型始终保留
            if allowed_ids is not None and menu.id not in allowed_ids and menu.type != 1 and not children:
                continue
            node = {
                "id": menu.id,
                "label": menu.label,
                "labelEn": menu.label_en,
                "title": menu.label,
                "titleEn": menu.label_en,
                "key": menu.router,
                "value": str(menu.id),
                "icon": menu.icon,
                "type": menu.type,
                "router": menu.router,
                "rule": menu.permission.name if menu.permission else None,
                "order": menu.order,
                "state": menu.state,
                "parentId": menu.parent_id,
                "permissionId": menu.permission_id,
                "createdAt": format_datetime(menu.create_at),
                "updatedAt": format_datetime(menu.update_at),
            }
            if children:
                node["children"] = children
            tree.append(node)
    return tree
