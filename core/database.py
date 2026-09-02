from config.database import async_engine, sync_engine
from models.base import Base

# 导入所有模型，确保 Base.metadata 能发现它们
from models.system.user import SysUser
from models.system.role import SysRole
from models.system.menu import SysMenu
from models.system.permission import SysPermission
from models.system.log import SysLog
from models.system.article import SysArticle


async def create_tables():
    # 使用同步引擎创建表（避免 greenlet 问题）
    Base.metadata.create_all(sync_engine)
