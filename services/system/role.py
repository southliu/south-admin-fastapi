from datetime import UTC, datetime

from sqlalchemy import and_, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from models.base import format_datetime
from models.system.menu import SysMenu
from models.system.role import SysRole, role_menu
from models.system.user import user_role
from schemas.role import CreateRoleRequest, UpdateRoleRequest


async def get_role_by_id(
    db: AsyncSession,
    role_id: int,
) -> SysRole | None:
    """根据ID查询角色"""
    result = await db.execute(
        select(SysRole)
        .where(and_(SysRole.id == role_id, SysRole.is_deleted == 0))
        .options(
            selectinload(SysRole.menus),
            with_loader_criteria(SysMenu, SysMenu.is_deleted == 0),
        )
    )
    return result.scalar_one_or_none()


async def get_role_by_name(
    db: AsyncSession,
    name: str,
) -> SysRole | None:
    """根据名称查询角色"""
    result = await db.execute(
        select(SysRole).where(
            and_(SysRole.name == name, SysRole.is_deleted == 0)
        )
    )
    return result.scalar_one_or_none()


async def get_any_role_by_name(
    db: AsyncSession,
    name: str,
) -> SysRole | None:
    result = await db.execute(select(SysRole).where(SysRole.name == name))
    return result.scalar_one_or_none()


async def get_role_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    name: str | None = None,
) -> dict[str, object]:
    """获取角色分页列表"""
    query = select(SysRole).where(SysRole.is_deleted == 0)

    if name:
        query = query.where(SysRole.name.like(f"%{name}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

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

    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": (total + page_size - 1) // page_size,
    }


async def get_role_list(db: AsyncSession) -> list[SysRole]:
    """获取角色列表"""
    result = await db.execute(select(SysRole).where(SysRole.is_deleted == 0))
    return result.scalars().all()


async def get_roles_by_ids(
    db: AsyncSession,
    role_ids: list[int],
) -> list[SysRole]:
    """根据ID列表查询角色"""
    result = await db.execute(
        select(SysRole).where(
            and_(SysRole.id.in_(role_ids), SysRole.is_deleted == 0)
        )
    )
    return result.scalars().all()


async def create_role(db: AsyncSession, data: CreateRoleRequest) -> SysRole:
    """创建角色"""
    # 检查角色名是否已存在
    existing = await get_any_role_by_name(db, data.name)
    if existing:
        if existing.is_deleted == 0:
            raise ValueError("角色名已存在")
        existing.description = data.description
        existing.is_deleted = 0
        existing.deleted_at = None
        await update_role_menus(db, existing.id, data.authorize or [])
        return existing

    role = SysRole(
        name=data.name,
        description=data.description,
    )

    db.add(role)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("角色名已存在") from exc

    # 关联菜单
    if data.authorize:
        await update_role_menus(db, role.id, data.authorize)

    return role


async def update_role(
    db: AsyncSession, role_id: int, data: UpdateRoleRequest
) -> SysRole:
    """更新角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    # 检查角色名是否已存在
    if data.name != role.name:
        existing = await get_role_by_name(db, data.name)
        if existing:
            raise ValueError("角色名已存在")

    if role.name == "admin" and data.name != "admin":
        raise ValueError("系统管理员角色不能重命名")

    role.name = data.name
    role.description = data.description or None

    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("角色名已存在") from exc

    # 更新菜单关联
    await update_role_menus(db, role_id, data.authorize)

    return role


async def delete_role(db: AsyncSession, role_id: int) -> None:
    """删除角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")
    if role.name == "admin":
        raise ValueError("系统管理员角色不能删除")

    await db.execute(role_menu.delete().where(role_menu.c.role_id == role_id))
    await db.execute(user_role.delete().where(user_role.c.role_id == role_id))
    role.is_deleted = 1
    role.deleted_at = datetime.now(UTC)


async def get_role_authorize(db: AsyncSession, role_id: int) -> dict:
    """获取角色授权信息"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    role_menu_ids = {menu.id for menu in role.menus}
    default_checked_keys = [str(mid) for mid in role_menu_ids]

    # 查询所有菜单（用于构建完整树形结构）
    result = await db.execute(
        select(SysMenu)
        .where(and_(SysMenu.is_deleted == 0))
        .order_by(SysMenu.order)
    )
    all_menus = result.scalars().all()

    tree_data = _build_authorize_tree(all_menus, None)

    return {
        "defaultCheckedKeys": default_checked_keys,
        "treeData": tree_data,
    }


def _build_authorize_tree(
    menus: list[SysMenu],
    parent_id: int | None,
) -> list[dict[str, object]]:
    """构建完整授权菜单树，已选项由 defaultCheckedKeys 表达。"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = _build_authorize_tree(menus, menu.id)
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


async def save_role_authorize(
    db: AsyncSession,
    role_id: int,
    menu_ids: list[int],
) -> None:
    """保存角色授权"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    await update_role_menus(db, role_id, menu_ids)


async def update_role_menus(
    db: AsyncSession,
    role_id: int,
    menu_ids: list[int],
) -> None:
    """更新角色菜单关联"""
    # 删除原有菜单关联
    await db.execute(role_menu.delete().where(role_menu.c.role_id == role_id))

    if not menu_ids:
        return

    menus = await db.execute(
        select(SysMenu.id).where(
            SysMenu.id.in_(menu_ids),
            SysMenu.is_deleted == 0,
        )
    )
    existing_menu_ids = set(menus.scalars().all())
    if set(menu_ids) - existing_menu_ids:
        raise ValueError("包含不存在的菜单")

    await db.execute(
        insert(role_menu),
        [
            {"role_id": role_id, "menu_id": menu_id}
            for menu_id in dict.fromkeys(menu_ids)
        ],
    )
