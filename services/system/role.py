from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload, selectinload

from models.base import format_datetime
from models.system.menu import SysMenu
from models.system.role import SysRole, role_menu
from models.system.user import user_role
from schemas.role import CreateRoleRequest, UpdateRoleRequest
from services.system.access import is_admin, validate_role_grant


async def get_role_by_id(db: AsyncSession, role_id: int) -> SysRole | None:
    """根据ID查询角色"""
    result = await db.execute(
        select(SysRole)
        .options(raiseload("*"))
        .where(and_(SysRole.id == role_id, SysRole.is_deleted == 0))
        .options(selectinload(SysRole.menus.and_(SysMenu.is_deleted == 0)))
    )
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> SysRole | None:
    """根据名称查询角色"""
    result = await db.execute(
        select(SysRole)
        .options(raiseload("*"))
        .where(and_(SysRole.name == name, SysRole.is_deleted == 0))
    )
    return result.scalar_one_or_none()


async def get_role_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    name: str | None = None,
) -> dict[str, Any]:
    """获取角色分页列表"""
    query = (
        select(SysRole).options(raiseload("*")).where(SysRole.is_deleted == 0)
    )

    if name:
        query = query.where(SysRole.name.like(f"%{name}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = (
        query.offset(offset)
        .limit(page_size)
        .order_by(SysRole.create_at.desc())
    )
    result = await db.execute(query)
    roles = result.scalars().all()

    # 构建返回数据
    items = []
    for role in roles:
        items.append(
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "createdAt": format_datetime(role.create_at),
                "updatedAt": format_datetime(role.update_at),
            }
        )

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


async def get_role_list(db: AsyncSession) -> list[SysRole]:
    """获取角色列表"""
    result = await db.execute(
        select(SysRole).options(raiseload("*")).where(SysRole.is_deleted == 0)
    )
    return result.scalars().all()


async def get_roles_by_ids(
    db: AsyncSession, role_ids: list[int]
) -> list[SysRole]:
    """根据ID列表查询角色"""
    result = await db.execute(
        select(SysRole)
        .options(raiseload("*"))
        .where(and_(SysRole.id.in_(role_ids), SysRole.is_deleted == 0))
    )
    return result.scalars().all()


async def create_role(
    db: AsyncSession, data: CreateRoleRequest, actor_id: int
) -> SysRole:
    """创建角色"""
    await validate_role_grant(db, actor_id, data.name, data.authorize)
    # 检查角色名是否已存在
    existing = await get_role_by_name(db, data.name)
    if existing:
        raise ValueError("角色名已存在")

    role = SysRole(
        name=data.name,
        description=data.description,
    )

    db.add(role)
    await db.flush()
    await db.refresh(role)

    # 关联菜单
    if data.authorize:
        await update_role_menus(db, role.id, data.authorize)

    await db.flush()

    return role


async def update_role(
    db: AsyncSession, role_id: int, data: UpdateRoleRequest, actor_id: int
) -> SysRole:
    """更新角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    await validate_role_grant(
        db, actor_id, data.name, data.authorize, role.name
    )
    # 检查角色名是否已存在
    if data.name != role.name:
        existing = await get_role_by_name(db, data.name)
        if existing:
            raise ValueError("角色名已存在")

    role.name = data.name
    role.description = data.description or None

    await db.flush()

    # 更新菜单关联
    if data.authorize is not None:
        await update_role_menus(db, role_id, data.authorize)

    await db.flush()

    return role


async def delete_role(db: AsyncSession, role_id: int, actor_id: int) -> None:
    """删除角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    await validate_role_grant(db, actor_id, role.name, None)
    role.is_deleted = 1
    role.deleted_at = datetime.now()
    await db.flush()


async def get_role_authorize(
    db: AsyncSession, role_ids: str, actor_id: int
) -> dict[str, Any]:
    """按前端传入的当前用户角色集合构建可授权菜单树。"""
    ids = _parse_role_ids(role_ids)
    admin = await is_admin(db, actor_id)
    query = select(SysRole.id).where(
        SysRole.id.in_(ids), SysRole.is_deleted == 0
    )
    if not admin:
        query = query.join(user_role).where(user_role.c.user_id == actor_id)
    available_ids = set(await db.scalars(query))
    if available_ids != set(ids):
        raise ValueError("角色不存在或没有访问权限")
    granted_ids = set(
        await db.scalars(
            select(role_menu.c.menu_id)
            .join(SysMenu, SysMenu.id == role_menu.c.menu_id)
            .where(role_menu.c.role_id.in_(ids), SysMenu.is_deleted == 0)
        )
    )
    menus = list(
        await db.scalars(
            select(SysMenu)
            .options(raiseload("*"))
            .where(SysMenu.is_deleted == 0)
            .order_by(SysMenu.order, SysMenu.id)
        )
    )
    visible_ids = {menu.id for menu in menus} if admin else granted_ids
    return {
        "defaultCheckedKeys": [str(mid) for mid in sorted(granted_ids)],
        "treeData": _build_authorize_tree(menus, None, visible_ids),
    }


def _parse_role_ids(value: str) -> list[int]:
    parts = value.split(",")
    if not parts or any(
        not part.strip().isascii()
        or not part.strip().isdecimal()
        or len(part.strip()) > 10
        for part in parts
    ):
        raise ValueError("角色 ID 格式无效")
    ids = list(dict.fromkeys(int(part.strip()) for part in parts))
    if any(not 0 < role_id <= 2**31 - 1 for role_id in ids):
        raise ValueError("角色 ID 格式无效")
    return ids


def _build_authorize_tree(
    menus: Sequence[SysMenu],
    parent_id: int | None,
    role_menu_ids: set[int],
) -> list[dict[str, Any]]:
    """构建授权菜单树，保留已授权菜单及其祖先。"""
    menus_by_parent: dict[int | None, list[SysMenu]] = defaultdict(list)
    for menu in menus:
        menus_by_parent[menu.parent_id].append(menu)

    def build_children(current_parent_id: int | None) -> list[dict[str, Any]]:
        tree: list[dict[str, Any]] = []
        for menu in menus_by_parent.get(current_parent_id, ()):
            children = build_children(menu.id)
            if menu.id not in role_menu_ids and not children:
                continue
            node = {
                "title": menu.label,
                "value": str(menu.id),
                "key": str(menu.id),
                "type": menu.type,
                "icon": menu.icon,
            }
            if children:
                node["children"] = children
            tree.append(node)
        return tree

    return build_children(parent_id)


async def save_role_authorize(
    db: AsyncSession, role_id: int, menu_ids: list[int], actor_id: int
) -> None:
    """保存角色授权"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    await validate_role_grant(db, actor_id, role.name, menu_ids)
    await update_role_menus(db, role_id, menu_ids)
    await db.flush()


async def update_role_menus(
    db: AsyncSession, role_id: int, menu_ids: list[int]
) -> None:
    """更新角色菜单关联"""
    # 删除原有菜单关联
    await db.execute(role_menu.delete().where(role_menu.c.role_id == role_id))

    if not menu_ids:
        return

    await db.execute(
        role_menu.insert(),
        [{"role_id": role_id, "menu_id": menu_id} for menu_id in menu_ids],
    )
