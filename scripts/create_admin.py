import asyncio
import logging
import os

from sqlalchemy import select

from config.database import AsyncSessionLocal, async_engine
from core.database import MODEL_TYPES
from models.system.role import SysRole
from schemas.user import CreateUserRequest
from services.system.user import create_user

logger = logging.getLogger(__name__)
_ = MODEL_TYPES


async def create_admin() -> None:
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD")
    if password is None:
        raise RuntimeError("必须通过 ADMIN_PASSWORD 提供管理员密码")

    async with AsyncSessionLocal() as session:
        role = await session.scalar(
            select(SysRole).where(
                SysRole.name == "admin",
                SysRole.is_deleted == 0,
            )
        )
        if role is None:
            raise RuntimeError("请先执行 database/init.sql 创建 admin 角色")

        user = await create_user(
            session,
            CreateUserRequest(
                username=username,
                password=password,
                name="超级管理员",
                status=1,
                role_ids=[role.id],
            ),
        )
        await session.commit()
        logger.info("管理员已创建: %s", user.username)


async def main() -> None:
    try:
        await create_admin()
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
