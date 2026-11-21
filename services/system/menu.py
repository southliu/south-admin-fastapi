from datetime import UTC, datetime

from sqlalchemy import and_, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.base import format_datetime
from models.system.menu import SysMenu
from models.system.permission import SysPermission
from models.system.role import role_menu
from models.system.user import user_role
from schemas.menu import (
    ChangeMenuStateRequest,
    CreateMenuRequest,
    UpdateMenuRequest,
)
from services.system.permission import get_any_permission_by_name
from services.system.user import get_user_permission_names

# 按钮动作标签映射
ACTION_LABELS = {
    "create": ("新增", "Create"),
    "update": ("修改", "Update"),
    "delete": ("删除", "Delete"),
    "detail": ("详情", "Detail"),
    "export": ("导出权限", "Export"),
    "status": ("状态权限", "Status"),
}


def _collect_subtree_ids(
    parent_by_id: dict[int, int | None],
    root_ids: set[int],
) -> set[int]:
    subtree_ids = set(root_ids)
    while True:
        children = {
            menu_id
            for menu_id, parent_id in parent_by_id.items()
            if parent_id in subtree_ids and menu_id not in subtree_ids
        }
        if not children:
            return subtree_ids
        subtree_ids.update(children)


async def _get_subtree_ids(
    db: AsyncSession,
    root_ids: set[int],
) -> set[int]:
    rows = await db.execute(
        select(SysMenu.id, SysMenu.parent_id).where(SysMenu.is_deleted == 0)
    )
    parent_by_id = dict(rows.all())
    return _collect_subtree_ids(parent_by_id, root_ids)


async def _validate_parent(
    db: AsyncSession,
    parent_id: int | None,
    menu_id: int | None = None,
) -> None:
    if parent_id is None:
        return
    parent = await db.scalar(
        select(SysMenu).where(
            SysMenu.id == parent_id,
            SysMenu.is_deleted == 0,
        )
    )
    if parent is None:
        raise ValueError("父菜单不存在")
    if parent.type == 3:
        raise ValueError("按钮不能作为父菜单")
    if menu_id is None:
        return
    if parent_id == menu_id:
        raise ValueError("菜单不能作为自己的父菜单")
    if parent_id in await _get_subtree_ids(db, {menu_id}):
        raise ValueError("父菜单不能选择当前菜单的子孙节点")


async def get_or_create_permission(
    db: AsyncSession, name: str, description: str
) -> SysPermission:
    """获取或创建权限"""
    result = await db.execute(
        select(SysPermission).where(SysPermission.name == name)
    )
    permission = result.scalar_one_or_none()
    if permission:
        if permission.is_deleted:
            permission.is_deleted = 0
            permission.deleted_at = None
            permission.description = description
        return permission

    permission = SysPermission(name=name, description=description)
    db.add(permission)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("权限名已存在") from exc
    await db.refresh(permission)
    return permission


async def get_menu_by_id(
    db: AsyncSession,
    menu_id: int,
) -> SysMenu | None:
    """根据ID查询菜单"""
    result = await db.execute(
        select(SysMenu)
        .where(and_(SysMenu.id == menu_id, SysMenu.is_deleted == 0))
        .options(selectinload(SysMenu.permission))
        .options(selectinload(SysMenu.children))
    )
    return result.scalar_one_or_none()


async def get_menu_list(
    db: AsyncSession,
    user_id: int,
) -> list[dict[str, object]]:
    """获取用户菜单列表"""
    permission_names = await get_user_permission_names(db, user_id)
    if not permission_names:
        return []

    # 查询有权限的菜单ID（排除按钮类型）
    permitted_result = await db.execute(
        select(SysMenu.id)
        .join(SysPermission, SysMenu.permission_id == SysPermission.id)
        .where(
            SysPermission.name.in_(permission_names),
            SysMenu.is_deleted == 0,
            SysMenu.type != 3,
        )
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
    label: str | None = None,
    label_en: str | None = None,
    state: int | None = None,
    rule: str | None = None,
) -> dict[str, object]:
    """获取菜单分页列表（树形结构）"""
    query = (
        select(SysMenu)
        .where(SysMenu.is_deleted == 0)
        .options(selectinload(SysMenu.permission))
        .order_by(SysMenu.order, SysMenu.id)
    )
    result = await db.execute(query)
    menus = list(result.scalars().all())

    if any((label, label_en, state is not None, rule)):
        matching_ids = {
            menu.id
            for menu in menus
            if (not label or label in menu.label)
            and (not label_en or label_en in menu.label_en)
            and (state is None or menu.state == state)
            and (
                not rule
                or (
                    menu.permission is not None
                    and rule in menu.permission.name
                )
            )
        }
        menu_by_id = {menu.id: menu for menu in menus}
        visible_ids = set(matching_ids)
        for menu_id in matching_ids:
            parent_id = menu_by_id[menu_id].parent_id
            visited: set[int] = set()
            while parent_id is not None and parent_id not in visited:
                visited.add(parent_id)
                parent = menu_by_id.get(parent_id)
                if parent is None:
                    break
                visible_ids.add(parent_id)
                parent_id = parent.parent_id
        menus = [menu for menu in menus if menu.id in visible_ids]

    tree = build_menu_tree(menus, None, include_button=True)
    total = len(tree)
    offset = (page - 1) * page_size
    items = tree[offset : offset + page_size]

    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": (total + page_size - 1) // page_size,
    }


async def get_menu_detail(
    db: AsyncSession,
    menu_id: int,
) -> dict[str, object]:
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


async def create_menu(
    db: AsyncSession, data: CreateMenuRequest, user_id: int
) -> SysMenu:
    """创建菜单"""
    await _validate_parent(db, data.parent_id)
    if data.type == 3 and data.parent_id is None:
        raise ValueError("按钮必须归属于菜单")
    if data.actions and not data.rule:
        raise ValueError("创建按钮权限前必须填写菜单规则")

    permission_id = None

    # 如果有 rule，自动创建权限记录
    if data.rule:
        permission = await get_or_create_permission(db, data.rule, data.label)
        permission_id = permission.id

    menu = SysMenu(
        label=data.label,
        label_en=data.label_en,
        type=data.type,
        icon=data.icon or None,
        router=data.router or None,
        order=data.order,
        state=data.state,
        parent_id=data.parent_id,
        permission_id=permission_id,
    )

    db.add(menu)
    await db.flush()

    # 关联当前用户的角色与新菜单
    result = await db.execute(
        select(user_role.c.role_id).where(user_role.c.user_id == user_id)
    )
    role_ids = result.scalars().all()
    if role_ids:
        await db.execute(
            insert(role_menu),
            [{"role_id": role_id, "menu_id": menu.id} for role_id in role_ids],
        )

    # 根据 actions 创建按钮子菜单
    if data.actions and data.rule:
        for action in data.actions:
            labels = ACTION_LABELS[action]

            button_rule = f"{data.rule}/{action}"
            button_permission = await get_or_create_permission(
                db, button_rule, labels[0]
            )

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
            if role_ids:
                await db.execute(
                    insert(role_menu),
                    [
                        {"role_id": role_id, "menu_id": button_menu.id}
                        for role_id in role_ids
                    ],
                )

    return menu


async def update_menu(
    db: AsyncSession, menu_id: int, data: UpdateMenuRequest
) -> SysMenu:
    """更新菜单"""
    menu = await get_menu_by_id(db, menu_id)
    if not menu:
        raise ValueError("菜单不存在")

    menu.label = data.label
    menu.label_en = data.label_en

    await _validate_parent(db, data.parent_id, menu.id)
    if data.type == 3:
        has_children = await db.scalar(
            select(SysMenu.id)
            .where(
                SysMenu.parent_id == menu.id,
                SysMenu.is_deleted == 0,
            )
            .limit(1)
        )
        if has_children is not None:
            raise ValueError("存在子菜单的节点不能改为按钮")
        if data.parent_id is None:
            raise ValueError("按钮必须归属于菜单")

    # 可空字段：直接赋值，前端不传即为 None → 清空
    menu.icon = data.icon or None
    menu.router = data.router or None
    menu.parent_id = data.parent_id

    menu.type = data.type
    menu.order = data.order
    menu.state = data.state

    # 空 rule 仅解除关联，权限记录继续由权限管理维护。
    if data.rule:
        if menu.permission:
            if menu.permission.name != data.rule:
                existing = await get_any_permission_by_name(db, data.rule)
                if existing and existing.id != menu.permission_id:
                    existing.is_deleted = 0
                    existing.deleted_at = None
                    menu.permission = existing
                else:
                    menu.permission.name = data.rule
            menu.permission.is_deleted = 0
            menu.permission.deleted_at = None
            menu.permission.description = data.label
        else:
            menu.permission = await get_or_create_permission(
                db, data.rule, data.label
            )
    elif menu.permission:
        menu.permission = None

    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("权限名已存在") from exc
    return menu


async def delete_menu(db: AsyncSession, menu_id: int) -> None:
    """删除菜单"""
    menu = await get_menu_by_id(db, menu_id)
    if not menu:
        raise ValueError("菜单不存在")

    menu_ids = await _get_subtree_ids(db, {menu_id})
    await db.execute(
        role_menu.delete().where(role_menu.c.menu_id.in_(menu_ids))
    )
    await db.execute(
        update(SysMenu)
        .where(SysMenu.id.in_(menu_ids), SysMenu.is_deleted == 0)
        .values(is_deleted=1, deleted_at=datetime.now(UTC))
    )


async def batch_delete_menu(
    db: AsyncSession,
    menu_ids: list[int],
) -> None:
    """批量删除菜单"""
    menu_ids = await _get_subtree_ids(db, set(menu_ids))
    await db.execute(
        role_menu.delete().where(role_menu.c.menu_id.in_(menu_ids))
    )

    await db.execute(
        update(SysMenu)
        .where(SysMenu.id.in_(menu_ids), SysMenu.is_deleted == 0)
        .values(is_deleted=1, deleted_at=datetime.now(UTC))
    )


async def change_menu_state(
    db: AsyncSession, data: ChangeMenuStateRequest
) -> None:
    """修改菜单状态"""
    menu = await get_menu_by_id(db, data.id)
    if not menu:
        raise ValueError("菜单不存在")

    menu.state = data.state


def build_menu_tree(
    menus: list[SysMenu],
    parent_id: int | None,
    include_button: bool = False,
    allowed_ids: set[int] | None = None,
) -> list[dict[str, object]]:
    """构建菜单树形结构"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id and (include_button or menu.type != 3):
            children = build_menu_tree(
                menus, menu.id, include_button, allowed_ids
            )
            # 目录保留；其他节点必须有权限或包含有权限的子节点。
            if (
                allowed_ids is not None
                and menu.id not in allowed_ids
                and not children
            ):
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
