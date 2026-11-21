from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import format_datetime
from models.system.permission import SysPermission
from schemas.permission import CreatePermissionRequest, UpdatePermissionRequest


async def get_permission_by_id(
    db: AsyncSession,
    permission_id: int,
) -> SysPermission | None:
    """根据ID查询权限"""
    result = await db.execute(
        select(SysPermission).where(
            and_(
                SysPermission.id == permission_id,
                SysPermission.is_deleted == 0,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_permission_by_name(
    db: AsyncSession,
    name: str,
) -> SysPermission | None:
    """根据名称查询权限"""
    result = await db.execute(
        select(SysPermission).where(
            and_(SysPermission.name == name, SysPermission.is_deleted == 0)
        )
    )
    return result.scalar_one_or_none()


async def get_any_permission_by_name(
    db: AsyncSession,
    name: str,
) -> SysPermission | None:
    result = await db.execute(
        select(SysPermission).where(SysPermission.name == name)
    )
    return result.scalar_one_or_none()


async def get_permission_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    name: str | None = None,
) -> dict[str, object]:
    """获取权限分页列表"""
    query = select(SysPermission).where(SysPermission.is_deleted == 0)

    if name:
        query = query.where(SysPermission.name.like(f"%{name}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = (
        query.offset(offset)
        .limit(page_size)
        .order_by(SysPermission.create_at.desc())
    )
    result = await db.execute(query)
    permissions = result.scalars().all()

    # 构建返回数据
    items = []
    for permission in permissions:
        items.append(
            {
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
                "createdAt": format_datetime(permission.create_at),
                "updatedAt": format_datetime(permission.update_at),
            }
        )

    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": (total + page_size - 1) // page_size,
    }


async def get_permission_list(db: AsyncSession) -> list[SysPermission]:
    """获取权限列表"""
    result = await db.execute(
        select(SysPermission).where(SysPermission.is_deleted == 0)
    )
    return result.scalars().all()


async def create_permission(
    db: AsyncSession, data: CreatePermissionRequest
) -> SysPermission:
    """创建权限"""
    # 检查权限名是否已存在
    existing = await get_any_permission_by_name(db, data.name)
    if existing:
        if existing.is_deleted == 0:
            raise ValueError("权限名已存在")
        existing.description = data.description
        existing.is_deleted = 0
        existing.deleted_at = None
        return existing

    permission = SysPermission(
        name=data.name,
        description=data.description,
    )

    db.add(permission)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("权限名已存在") from exc
    return permission


async def update_permission(
    db: AsyncSession, permission_id: int, data: UpdatePermissionRequest
) -> SysPermission:
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
    permission.description = data.description or None

    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("权限名已存在") from exc
    return permission


async def delete_permission(db: AsyncSession, permission_id: int) -> None:
    """删除权限"""
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise ValueError("权限不存在")

    permission.is_deleted = 1
    permission.deleted_at = datetime.now(UTC)
