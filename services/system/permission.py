from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.system.permission import SysPermission
from models.base import format_datetime
from schemas.permission import CreatePermissionRequest, UpdatePermissionRequest


async def get_permission_by_id(db: AsyncSession, permission_id: int) -> Optional[SysPermission]:
    """根据ID查询权限"""
    result = await db.execute(
        select(SysPermission)
        .where(and_(SysPermission.id == permission_id, SysPermission.is_deleted == 0))
    )
    return result.scalar_one_or_none()


async def get_permission_by_name(db: AsyncSession, name: str) -> Optional[SysPermission]:
    """根据名称查询权限"""
    result = await db.execute(
        select(SysPermission)
        .where(and_(SysPermission.name == name, SysPermission.is_deleted == 0))
    )
    return result.scalar_one_or_none()


async def get_permission_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    name: Optional[str] = None
) -> dict:
    """获取权限分页列表"""
    query = select(SysPermission).where(SysPermission.is_deleted == 0)

    if name:
        query = query.where(SysPermission.name.like(f"%{name}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(SysPermission.create_at.desc())
    result = await db.execute(query)
    permissions = result.scalars().all()

    # 构建返回数据
    items = []
    for permission in permissions:
        items.append({
            "id": permission.id,
            "name": permission.name,
            "description": permission.description,
            "createdAt": format_datetime(permission.create_at),
            "updatedAt": format_datetime(permission.update_at),
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


async def get_permission_list(db: AsyncSession) -> List[SysPermission]:
    """获取权限列表"""
    result = await db.execute(
        select(SysPermission).where(SysPermission.is_deleted == 0)
    )
    return result.scalars().all()


async def create_permission(db: AsyncSession, data: CreatePermissionRequest) -> SysPermission:
    """创建权限"""
    # 检查权限名是否已存在
    existing = await get_permission_by_name(db, data.name)
    if existing:
        raise ValueError("权限名已存在")

    permission = SysPermission(
        name=data.name,
        description=data.description,
    )

    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    return permission


async def update_permission(db: AsyncSession, permission_id: int, data: UpdatePermissionRequest) -> SysPermission:
    """更新权限"""
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise ValueError("权限不存在")

    # 检查权限名是否已存在
    if data.name != permission.name:
        existing = await get_permission_by_name(db, data.name)
        if existing:
            raise ValueError("权限名已存在")

    permission.name = data.name
    if data.description is not None:
        permission.description = data.description

    await db.commit()
    await db.refresh(permission)
    return permission


async def delete_permission(db: AsyncSession, permission_id: int) -> None:
    """删除权限"""
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise ValueError("权限不存在")

    from datetime import datetime
    permission.is_deleted = 1
    permission.deleted_at = datetime.now()
    await db.commit()
