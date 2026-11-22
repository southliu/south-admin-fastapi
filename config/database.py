from collections.abc import AsyncIterator
from pathlib import Path

import yaml
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_config_path = Path(__file__).parent.parent / "config.yaml"

with open(_config_path, encoding="utf-8") as f:
    _config = yaml.safe_load(f)

ASYNC_DATABASE_URL = _config["database"]["url"]

# 保留同步连接供离线维护脚本使用。
SYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace(
    "mysql+aiomysql", "mysql+pymysql"
)

sync_engine = create_engine(
    SYNC_DATABASE_URL, echo=False, hide_parameters=True
)

# 异步引擎（用于正常操作）
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    hide_parameters=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal.begin() as session:
        yield session
