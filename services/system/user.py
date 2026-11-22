from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload, selectinload

from models.base import format_datetime
from models.system.menu import SysMenu
from models.system.permission import SysPermission
from models.system.role import SysRole, role_menu
from models.system.user import SysUser, user_role
from schemas.user import CreateUserRequest, UpdateUserRequest
from services.system.access import validate_user_grant
from utils.security import hash_password, verify_password


async def get_user_by_username(
    db: AsyncSession, username: str
) -> SysUser | None:
    """根据用户名查询用户"""
    result = await db.execute(
        select(SysUser)
        .where(and_(SysUser.username == username, SysUser.is_deleted == 0))
        .options(
            raiseload("*"),
            selectinload(SysUser.roles.and_(SysRole.is_deleted == 0))
            .selectinload(SysRole.menus)
            .selectinload(SysMenu.permission),
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> SysUser | None:
    """根据ID查询用户"""
    result = await db.execute(
        select(SysUser)
        .where(and_(SysUser.id == user_id, SysUser.is_deleted == 0))
        .options(
            raiseload("*"),
            selectinload(SysUser.roles.and_(SysRole.is_deleted == 0))
            .selectinload(SysRole.menus)
            .selectinload(SysMenu.permission),
        )
    )
    return result.scalar_one_or_none()


async def get_user_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    username: str | None = None,
) -> dict[str, Any]:
    """获取用户分页列表"""
    query = select(SysUser).where(SysUser.is_deleted == 0)

    if username:
        query = query.where(SysUser.username.like(f"%{username}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = (
        query.options(
            raiseload("*"),
            selectinload(SysUser.roles.and_(SysRole.is_deleted == 0)),
        )
        .offset(offset)
        .limit(page_size)
        .order_by(SysUser.create_at.desc())
    )
    result = await db.execute(query)
    users = result.scalars().all()

    # 构建返回数据
    items = []
    for user in users:
        role_names = [role.name for role in user.roles]
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "phone": user.phone,
                "email": user.email,
                "status": user.status,
                "roles": [
                    {"id": role.id, "name": role.name} for role in user.roles
                ],
                "rolesName": ",".join(role_names),
                "roleCount": len(user.roles),
                "createdAt": format_datetime(user.create_at),
                "updatedAt": format_datetime(user.update_at),
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


async def get_user_list(db: AsyncSession) -> list[SysUser]:
    """获取用户列表"""
    result = await db.execute(
        select(SysUser)
        .where(and_(SysUser.is_deleted == 0, SysUser.status == 1))
        .options(
            raiseload("*"),
            selectinload(SysUser.roles.and_(SysRole.is_deleted == 0)),
        )
    )
    return result.scalars().all()


async def create_user(
    db: AsyncSession, data: CreateUserRequest, actor_id: int
) -> SysUser:
    """创建用户"""
    await validate_user_grant(db, actor_id, data.role_ids)
    # 检查用户名是否已存在
    existing = await get_user_by_username(db, data.username)
    if existing:
        raise ValueError("用户名已存在")

    # 加密密码
    hashed_password = await hash_password(data.password)

    user = SysUser(
        username=data.username,
        password=hashed_password,
        name=data.name,
        email=data.email,
        phone=data.phone,
        status=data.status,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    # 关联角色
    if data.role_ids:
        await update_user_roles(db, user.id, data.role_ids)

    await db.flush()

    return user


async def update_user(
    db: AsyncSession, user_id: int, data: UpdateUserRequest, actor_id: int
) -> SysUser:
    """更新用户"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    await validate_user_grant(db, actor_id, data.role_ids, user_id)
    # 检查用户名是否已存在
    if data.username != user.username:
        existing = await get_user_by_username(db, data.username)
        if existing:
            raise ValueError("用户名已存在")

    user.username = data.username
    if data.password:
        user.password = await hash_password(data.password)
    user.name = data.name or None
    user.email = data.email or None
    user.phone = data.phone or None
    if data.status is not None:
        user.status = data.status

    await db.flush()

    # 更新角色关联
    if data.role_ids is not None:
        await update_user_roles(db, user_id, data.role_ids)

    await db.flush()

    return user


async def delete_user(db: AsyncSession, user_id: int, actor_id: int) -> None:
    """删除用户"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    await validate_user_grant(db, actor_id, None, user_id)
    user.is_deleted = 1
    user.deleted_at = datetime.now()
    await db.flush()


async def update_user_password(
    db: AsyncSession, user_id: int, old_password: str, new_password: str
) -> None:
    """更新密码"""

    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    if not await verify_password(old_password, user.password):
        raise ValueError("旧密码错误")

    user.password = await hash_password(new_password)
    await db.flush()


async def update_user_roles(
    db: AsyncSession, user_id: int, role_ids: list[int]
) -> None:
    """更新用户角色关联"""
    # 删除原有角色关联
    await db.execute(user_role.delete().where(user_role.c.user_id == user_id))

    if not role_ids:
        return

    await db.execute(
        user_role.insert(),
        [{"user_id": user_id, "role_id": role_id} for role_id in role_ids],
    )


async def get_user_identity(db: AsyncSession, user_id: int) -> SysUser | None:
    return await db.scalar(
        select(SysUser)
        .where(SysUser.id == user_id, SysUser.is_deleted == 0)
        .options(raiseload("*"))
    )


async def get_user_access(
    db: AsyncSession, user_id: int
) -> tuple[bool, set[str]]:
    roles = await db.execute(
        select(SysRole.id, SysRole.name)
        .join(user_role, user_role.c.role_id == SysRole.id)
        .where(user_role.c.user_id == user_id, SysRole.is_deleted == 0)
    )
    role_rows = roles.all()
    permissions = await db.scalars(
        select(SysPermission.name)
        .join(SysMenu, SysMenu.permission_id == SysPermission.id)
        .join(role_menu, role_menu.c.menu_id == SysMenu.id)
        .where(
            role_menu.c.role_id.in_([role.id for role in role_rows]),
            SysMenu.is_deleted == 0,
            SysPermission.is_deleted == 0,
        )
    )
    return any(role.name == "admin" for role in role_rows), set(permissions)
