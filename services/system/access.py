from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.system.menu import SysMenu
from models.system.role import SysRole, role_menu
from models.system.user import user_role


async def is_admin(db: AsyncSession, user_id: int) -> bool:
    return (
        await db.scalar(
            select(SysRole.id)
            .join(user_role, user_role.c.role_id == SysRole.id)
            .where(
                user_role.c.user_id == user_id,
                SysRole.name == "admin",
                SysRole.is_deleted == 0,
            )
            .limit(1)
        )
        is not None
    )


async def validate_user_grant(
    db: AsyncSession,
    actor_id: int,
    role_ids: list[int] | None,
    target_id: int | None = None,
) -> None:
    if await is_admin(db, actor_id):
        return
    if target_id is not None and await is_admin(db, target_id):
        raise ValueError("不能修改管理员账号")
    owned = set(
        await db.scalars(
            select(SysRole.id)
            .join(user_role, user_role.c.role_id == SysRole.id)
            .where(user_role.c.user_id == actor_id, SysRole.is_deleted == 0)
        )
    )
    if role_ids is not None and not set(role_ids).issubset(owned):
        raise ValueError("不能分配自己未持有的角色")


async def validate_role_grant(
    db: AsyncSession,
    actor_id: int,
    name: str,
    menu_ids: list[int] | None,
    existing_name: str | None = None,
) -> None:
    if await is_admin(db, actor_id):
        return
    if "admin" in (name, existing_name):
        raise ValueError("不能修改管理员角色")
    owned = set(
        await db.scalars(
            select(SysMenu.id)
            .join(role_menu, role_menu.c.menu_id == SysMenu.id)
            .join(SysRole, SysRole.id == role_menu.c.role_id)
            .join(user_role, user_role.c.role_id == SysRole.id)
            .where(
                user_role.c.user_id == actor_id,
                SysRole.is_deleted == 0,
                SysMenu.is_deleted == 0,
            )
        )
    )
    if menu_ids is not None and not set(menu_ids).issubset(owned):
        raise ValueError("不能授予自己未持有的菜单权限")
