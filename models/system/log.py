from sqlalchemy import BigInteger, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class SysLog(Base):
    __tablename__ = "sys_log"
    __table_args__ = (
        Index("ix_sys_log_created", "create_at"),
        Index(
            "ix_sys_log_user_type_created",
            "username",
            "type",
            "create_at",
        ),
    )

    username: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="用户名"
    )
    ip: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="IP地址"
    )
    method: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="请求方法"
    )
    url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="请求地址"
    )
    params: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="请求参数"
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="User-Agent"
    )
    status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="状态"
    )
    error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    latency: Mapped[int] = mapped_column(
        BigInteger, default=0, comment="耗时(ms)"
    )
    type: Mapped[int] = mapped_column(
        Integer, default=0, comment="类型 0=后端错误 1=成功 2=警告 3=前端错误"
    )

    def __repr__(self):
        return (
            f"<SysLog(id={self.id}, username={self.username}, url={self.url})>"
        )
