from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_datetime(dt: datetime | None) -> str | None:
    """格式化时间为 YYYY-MM-DD HH:mm:ss"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
    )
    create_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        comment="创建时间",
    )
    update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        comment="更新时间",
    )
