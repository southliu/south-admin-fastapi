from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.system.menu import SysMenu
    from models.system.user import SysUser

# 角色-菜单关联表
role_menu = Table(
    "sys_role_menu",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("sys_role.id"), primary_key=True),
    Column("menu_id", Integer, ForeignKey("sys_menu.id"), primary_key=True),
)


class SysRole(Base):
    __tablename__ = "sys_role"
    __table_args__ = (
        Index("ix_sys_role_active_created", "is_deleted", "create_at"),
    )

    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="角色名称"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="描述"
    )
    is_deleted: Mapped[int] = mapped_column(
        Integer, default=0, comment="是否删除"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="删除时间"
    )

    # 关联关系
    users: Mapped[list[SysUser]] = relationship(
        "SysUser",
        secondary="sys_user_role",
        back_populates="roles",
        lazy="selectin",
    )
    menus: Mapped[list[SysMenu]] = relationship(
        "SysMenu",
        secondary=role_menu,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<SysRole(id={self.id}, name={self.name})>"
