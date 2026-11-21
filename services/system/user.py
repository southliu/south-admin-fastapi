from datetime import UTC, datetime

from sqlalchemy import and_, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from models.base import format_datetime
from models.system.menu import SysMenu
from models.system.permission import SysPermission
from models.system.role import SysRole, role_menu
from models.system.user import SysUser, user_role
from schemas.user import CreateUserRequest, UpdateUserRequest
from utils.security import hash_password_async, verify_password_async


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> SysUser | None:
    """根据用户名查询用户"""
    result = await db.execute(
        select(SysUser).where(
            and_(
                SysUser.username == username,
                SysUser.is_deleted == 0,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_any_user_by_username(
    db: AsyncSession,
    username: str,
) -> SysUser | None:
    result = await db.execute(
        select(SysUser).where(SysUser.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_identity_by_id(
    db: AsyncSession,
    user_id: int,
) -> SysUser | None:
    result = await db.execute(
        select(SysUser).where(
            and_(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> SysUser | None:
    """根据ID查询用户"""
    result = await db.execute(
        select(SysUser)
        .where(and_(SysUser.id == user_id, SysUser.is_deleted == 0))
        .options(
            selectinload(SysUser.roles)
            .selectinload(SysRole.menus)
            .selectinload(SysMenu.permission),
            with_loader_criteria(
                SysRole,
                SysRole.is_deleted == 0,
            ),
            with_loader_criteria(
                SysMenu,
                SysMenu.is_deleted == 0,
            ),
            with_loader_criteria(
                SysPermission,
                SysPermission.is_deleted == 0,
            ),
        )
    )
    return result.scalar_one_or_none()


async def get_user_permission_names(
    db: AsyncSession,
    user_id: int,
) -> set[str]:
    if await user_has_role(db, user_id, "admin"):
        result = await db.execute(
            select(SysPermission.name).where(SysPermission.is_deleted == 0)
        )
        return set(result.scalars().all())

    result = await db.execute(
        select(SysPermission.name)
        .select_from(SysPermission)
        .join(SysMenu, SysMenu.permission_id == SysPermission.id)
        .join(role_menu, role_menu.c.menu_id == SysMenu.id)
        .join(SysRole, SysRole.id == role_menu.c.role_id)
        .join(user_role, user_role.c.role_id == role_menu.c.role_id)
        .where(
            user_role.c.user_id == user_id,
            SysPermission.is_deleted == 0,
            SysMenu.is_deleted == 0,
            SysRole.is_deleted == 0,
        )
        .distinct()
    )
    return set(result.scalars().all())


async def get_user_role_ids(
    db: AsyncSession,
    user_id: int,
) -> list[int]:
    result = await db.execute(
        select(user_role.c.role_id)
        .join(SysRole, SysRole.id == user_role.c.role_id)
        .where(
            user_role.c.user_id == user_id,
            SysRole.is_deleted == 0,
        )
    )
    return list(result.scalars().all())


async def user_has_role(
    db: AsyncSession,
    user_id: int,
    role_name: str,
) -> bool:
    result = await db.execute(
        select(SysRole.id)
        .join(user_role, user_role.c.role_id == SysRole.id)
        .where(
            user_role.c.user_id == user_id,
            SysRole.name == role_name,
            SysRole.is_deleted == 0,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_user_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    username: str | None = None,
) -> dict[str, object]:
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
            selectinload(SysUser.roles),
            with_loader_criteria(SysRole, SysRole.is_deleted == 0),
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
        .options(selectinload(SysUser.roles))
    )
    return result.scalars().all()


async def create_user(db: AsyncSession, data: CreateUserRequest) -> SysUser:
    """创建用户"""
    # 检查用户名是否已存在
    existing = await get_any_user_by_username(db, data.username)
    if existing:
        if existing.is_deleted == 0:
            raise ValueError("用户名已存在")
        existing.password = await hash_password_async(data.password)
        existing.name = data.name
        existing.email = str(data.email) if data.email else None
        existing.phone = data.phone
        existing.status = data.status
        existing.is_deleted = 0
        existing.deleted_at = None
        existing.token_version += 1
        await update_user_roles(db, existing.id, list(data.role_ids))
        return existing

    # 加密密码
    hashed_password = await hash_password_async(data.password)

    user = SysUser(
        username=data.username,
        password=hashed_password,
        name=data.name,
        email=str(data.email) if data.email else None,
        phone=data.phone,
        status=data.status,
    )

    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("用户名已存在") from exc

    # 关联角色
    if data.role_ids:
        await update_user_roles(db, user.id, data.role_ids)

    return user


async def update_user(
    db: AsyncSession, user_id: int, data: UpdateUserRequest
) -> SysUser:
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
        user.password = await hash_password_async(data.password)
    user.name = data.name or None
    user.email = str(data.email) if data.email else None
    user.phone = data.phone or None
    if data.status != user.status:
        user.token_version += 1
    user.status = data.status

    try:
        await db.flush()
    except IntegrityError as exc:
        raise ValueError("用户名已存在") from exc

    # 更新角色关联
    await update_user_roles(db, user_id, data.role_ids)

    return user


async def delete_user(db: AsyncSession, user_id: int) -> None:
    """删除用户"""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    user.is_deleted = 1
    user.deleted_at = datetime.now(UTC)
    user.token_version += 1
    await db.execute(user_role.delete().where(user_role.c.user_id == user_id))


async def update_user_password(
    db: AsyncSession, user_id: int, old_password: str, new_password: str
) -> None:
    """更新密码"""
    user = await get_user_identity_by_id(db, user_id)
    if not user:
        raise ValueError("用户不存在")

    if not await verify_password_async(old_password, user.password):
        raise ValueError("旧密码错误")

    user.password = await hash_password_async(new_password)
    user.token_version += 1


async def revoke_user_tokens(db: AsyncSession, user_id: int) -> None:
    user = await get_user_identity_by_id(db, user_id)
    if user is None:
        raise ValueError("用户不存在")
    user.token_version += 1


async def update_user_roles(
    db: AsyncSession,
    user_id: int,
    role_ids: list[int],
) -> None:
    """更新用户角色关联"""
    # 删除原有角色关联
    await db.execute(user_role.delete().where(user_role.c.user_id == user_id))

    if not role_ids:
        return

    roles = await db.execute(
        select(SysRole.id).where(
            SysRole.id.in_(role_ids),
            SysRole.is_deleted == 0,
        )
    )
    existing_role_ids = set(roles.scalars().all())
    missing_role_ids = set(role_ids) - existing_role_ids
    if missing_role_ids:
        raise ValueError("包含不存在的角色")

    await db.execute(
        insert(user_role),
        [
            {"user_id": user_id, "role_id": role_id}
            for role_id in dict.fromkeys(role_ids)
        ],
    )
