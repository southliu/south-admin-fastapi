from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.system.user import SysUser, user_role
from models.system.role import SysRole
from models.system.menu import SysMenu
from models.base import format_datetime
from schemas.user import CreateUserRequest, UpdateUserRequest
from utils.security import hash_password


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[SysUser]:
    """根据用户名查询用户"""
    result = await db.execute(
        select(SysUser)
        .where(and_(SysUser.username == username, SysUser.is_deleted == 0))
        .options(
            selectinload(SysUser.roles).selectinload(SysRole.menus).selectinload(SysMenu.permission),
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[SysUser]:
    """根据ID查询用户"""
    result = await db.execute(
        select(SysUser)
        .where(and_(SysUser.id == user_id, SysUser.is_deleted == 0))
        .options(
            selectinload(SysUser.roles).selectinload(SysRole.menus).selectinload(SysMenu.permission),
        )
    )
    return result.scalar_one_or_none()


async def get_user_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    username: Optional[str] = None
) -> dict:
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
    query = query.options(selectinload(SysUser.roles)).offset(offset).limit(page_size).order_by(SysUser.create_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    # 构建返回数据
    items = []
    for user in users:
        role_names = [role.name for role in user.roles]
        items.append({
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "phone": user.phone,
            "email": user.email,
            "status": user.status,
            "roles": [{"id": role.id, "name": role.name} for role in user.roles],
            "rolesName": ",".join(role_names),
            "roleCount": len(user.roles),
            "createdAt": format_datetime(user.create_at),
            "updatedAt": format_datetime(user.update_at),
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


async def get_user_list(db: AsyncSession) -> List[SysUser]:
    """获取用户列表"""
    result = await db.execute(
        select(SysUser)
        .where(and_(SysUser.is_deleted == 0, SysUser.status == 1))
        .options(selectinload(SysUser.roles))
    )
    return result.scalars().all()


async def create_user(db: AsyncSession, data: CreateUserRequest) -> SysUser:
    """创建用户"""
    # 检查用户名是否已存在
    existing = await get_user_by_username(db, data.username)
    if existing:
        raise ValueError("用户名已存在")

    # 加密密码
    hashed_password = hash_password(data.password)

    user = SysUser(
        username=data.username,
        password=hashed_password,
        name=data.name,
        email=data.email,
        phone=data.phone,
        status=data.status or 1,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    # 关联角色
    if data.role_ids:
        await update_user_roles(db, user.id, data.role_ids)

    await db.commit()

    return user


async def update_user(db: AsyncSession, user_id: int, data: UpdateUserRequest) -> SysUser:
    """更新用户"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    # 检查用户名是否已存在
    if data.username != user.username:
        existing = await get_user_by_username(db, data.username)
        if existing:
            raise ValueError("用户名已存在")

    user.username = data.username
    if data.password:
        user.password = hash_password(data.password)
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.phone is not None:
        user.phone = data.phone
    if data.status is not None:
        user.status = data.status

    await db.flush()

    # 更新角色关联
    if data.role_ids is not None:
        await update_user_roles(db, user_id, data.role_ids)

    await db.commit()

    return user


async def delete_user(db: AsyncSession, user_id: int) -> None:
    """删除用户"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    from datetime import datetime
    user.is_deleted = 1
    user.deleted_at = datetime.now()
    await db.commit()


async def update_user_password(db: AsyncSession, user_id: int, old_password: str, new_password: str) -> None:
    """更新密码"""
    from utils.security import verify_password

    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    if not verify_password(old_password, user.password):
        raise ValueError("旧密码错误")

    user.password = hash_password(new_password)
    await db.commit()


async def update_user_roles(db: AsyncSession, user_id: int, role_ids: List[int]) -> None:
    """更新用户角色关联"""
    # 删除原有角色关联
    await db.execute(
        user_role.delete().where(user_role.c.user_id == user_id)
    )

    if not role_ids:
        return

    # 添加新的角色关联
    for role_id in role_ids:
        await db.execute(
            user_role.insert().values(user_id=user_id, role_id=role_id)
        )
