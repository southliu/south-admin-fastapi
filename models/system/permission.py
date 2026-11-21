from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.system.menu import SysMenu


class SysPermission(Base):
    __tablename__ = "sys_permission"
    __table_args__ = (
        Index(
            "ix_sys_permission_active_created",
            "is_deleted",
            "create_at",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="权限名称"
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
    menus: Mapped[list[SysMenu]] = relationship(
        "SysMenu",
        back_populates="permission",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<SysPermission(id={self.id}, name={self.name})>"
