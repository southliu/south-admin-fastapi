from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class SysArticle(Base):
    __tablename__ = "sys_article"

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="标题")
    author: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="作者")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容")
    demo: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="嵌套示例数据")
    creator: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="创建人")
    updater: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="更新人")
    is_deleted: Mapped[int] = mapped_column(Integer, default=0, comment="是否删除")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="删除时间")

    def __repr__(self):
        return f"<SysArticle(id={self.id}, title={self.title})>"
