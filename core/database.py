# 导入所有模型，确保 Base.metadata 能发现它们
from models.system.article import SysArticle
from models.system.log import SysLog
from models.system.menu import SysMenu
from models.system.permission import SysPermission
from models.system.role import SysRole
from models.system.user import SysUser

MODEL_TYPES = (
    SysArticle,
    SysLog,
    SysMenu,
    SysPermission,
    SysRole,
    SysUser,
)
