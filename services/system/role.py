from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.system.role import SysRole, role_menu
from models.system.menu import SysMenu
from models.system.permission import SysPermission
from models.base import format_datetime
from schemas.role import CreateRoleRequest, UpdateRoleRequest


async def get_role_by_id(db: AsyncSession, role_id: int) -> Optional[SysRole]:
    """根据ID查询角色"""
    result = await db.execute(
        select(SysRole)
        .where(and_(SysRole.id == role_id, SysRole.is_deleted == 0))
        .options(selectinload(SysRole.menus))
    )
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Optional[SysRole]:
    """根据名称查询角色"""
    result = await db.execute(
        select(SysRole)
        .where(and_(SysRole.name == name, SysRole.is_deleted == 0))
    )
    return result.scalar_one_or_none()


async def get_role_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    name: Optional[str] = None
) -> dict:
    """获取角色分页列表"""
    query = select(SysRole).where(SysRole.is_deleted == 0)

    if name:
        query = query.where(SysRole.name.like(f"%{name}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = query.options(selectinload(SysRole.menus)).offset(offset).limit(page_size).order_by(SysRole.create_at.desc())
    result = await db.execute(query)
    roles = result.scalars().all()

    # 构建返回数据
    items = []
    for role in roles:
        items.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "createdAt": format_datetime(role.create_at),
            "updatedAt": format_datetime(role.update_at),
        })

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


async def get_role_list(db: AsyncSession) -> List[SysRole]:
    """获取角色列表"""
    result = await db.execute(
        select(SysRole).where(SysRole.is_deleted == 0)
    )
    return result.scalars().all()


async def get_roles_by_ids(db: AsyncSession, role_ids: List[int]) -> List[SysRole]:
    """根据ID列表查询角色"""
    result = await db.execute(
        select(SysRole)
        .where(and_(SysRole.id.in_(role_ids), SysRole.is_deleted == 0))
    )
    return result.scalars().all()


async def create_role(db: AsyncSession, data: CreateRoleRequest) -> SysRole:
    """创建角色"""
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

    await db.commit()

    return role


async def update_role(db: AsyncSession, role_id: int, data: UpdateRoleRequest) -> SysRole:
    """更新角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    # 检查角色名是否已存在
    if data.name != role.name:
        existing = await get_role_by_name(db, data.name)
        if existing:
            raise ValueError("角色名已存在")

    role.name = data.name
    if data.description is not None:
        role.description = data.description

    await db.flush()

    # 更新菜单关联
    if data.authorize is not None:
        await update_role_menus(db, role_id, data.authorize)

    await db.commit()

    return role


async def delete_role(db: AsyncSession, role_id: int) -> None:
    """删除角色"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    from datetime import datetime
    role.is_deleted = 1
    role.deleted_at = datetime.now()
    await db.commit()


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

    tree_data = _build_authorize_tree(all_menus, None, role_menu_ids)

    return {
        "defaultCheckedKeys": default_checked_keys,
        "treeData": tree_data,
    }


def _build_authorize_tree(menus: List[SysMenu], parent_id: Optional[int], role_menu_ids: set) -> List[dict]:
    """构建授权菜单树（只包含当前角色拥有的菜单）"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = _build_authorize_tree(menus, menu.id, role_menu_ids)
            # 只保留角色拥有的菜单或包含子菜单的父级
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


async def save_role_authorize(db: AsyncSession, role_id: int, menu_ids: List[int]) -> None:
    """保存角色授权"""
    role = await get_role_by_id(db, role_id)
    if not role:
        raise ValueError("角色不存在")

    await update_role_menus(db, role_id, menu_ids)
    await db.commit()


async def update_role_menus(db: AsyncSession, role_id: int, menu_ids: List[int]) -> None:
    """更新角色菜单关联"""
    # 删除原有菜单关联
    await db.execute(
        role_menu.delete().where(role_menu.c.role_id == role_id)
    )

    if not menu_ids:
        return

    # 添加新的菜单关联
    for menu_id in menu_ids:
        await db.execute(
            role_menu.insert().values(role_id=role_id, menu_id=menu_id)
        )
