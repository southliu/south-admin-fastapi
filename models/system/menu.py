from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.system.permission import SysPermission
    from models.system.role import SysRole


class SysMenu(Base):
    __tablename__ = "sys_menu"
    __table_args__ = (
        Index(
            "ix_sys_menu_tree",
            "is_deleted",
            "state",
            "parent_id",
            "order",
        ),
    )

    label: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="菜单名称"
    )
    label_en: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="英文名称"
    )
    icon: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="图标"
    )
    type: Mapped[int] = mapped_column(
        Integer, comment="类型 1=目录 2=菜单 3=按钮"
    )
    router: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="路由地址"
    )
    order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    state: Mapped[int] = mapped_column(
        Integer, default=1, comment="状态 0=隐藏 1=显示"
    )
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_menu.id"), nullable=True, comment="父菜单ID"
    )
    permission_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_permission.id"),
        nullable=True,
        comment="权限ID",
    )
    is_deleted: Mapped[int] = mapped_column(
        Integer, default=0, comment="是否删除"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="删除时间"
    )

    # 关联关系
    parent: Mapped[SysMenu | None] = relationship(
        "SysMenu",
        remote_side="SysMenu.id",
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[list[SysMenu]] = relationship(
        "SysMenu",
        back_populates="parent",
        lazy="selectin",
    )
    permission: Mapped[SysPermission | None] = relationship(
        "SysPermission",
        back_populates="menus",
        lazy="selectin",
    )
    roles: Mapped[list[SysRole]] = relationship(
        "SysRole",
        secondary="sys_role_menu",
        back_populates="menus",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<SysMenu(id={self.id}, label={self.label}, type={self.type})>"
