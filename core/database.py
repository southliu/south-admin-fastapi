from importlib import import_module

from config.database import async_engine
from models.base import Base


async def create_tables() -> None:
    for name in ("article", "log", "menu", "permission", "role", "user"):
        import_module(f"models.system.{name}")
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
