from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import format_datetime
from models.system.log import SysLog
from schemas.log import CreateLogRequest


async def create_log(db: AsyncSession, data: CreateLogRequest) -> SysLog:
    log = SysLog(
        username=data.username,
        ip=data.ip,
        method=data.method,
        url=data.url,
        params=data.params,
        user_agent=data.user_agent,
        status=data.status,
        error=data.error,
        latency=data.latency,
        type=data.type,
    )
    db.add(log)
    await db.flush()
    return log


async def purge_expired_logs(
    db: AsyncSession,
    retention_days: int,
) -> None:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    await db.execute(delete(SysLog).where(SysLog.create_at < cutoff))


async def get_log_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    username: str | None = None,
    log_type: int = -1,
) -> dict[str, object]:
    query = select(SysLog)
    if username:
        query = query.where(SysLog.username.like(f"%{username}%"))
    if log_type >= 0:
        query = query.where(SysLog.type == log_type)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    total = total or 0
    query = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .order_by(SysLog.create_at.desc())
    )
    logs = (await db.execute(query)).scalars().all()

    return {
        "items": [
            {
                "id": log.id,
                "username": log.username,
                "ip": log.ip,
                "method": log.method,
                "url": log.url,
                "status": log.status,
                "error": log.error,
                "type": log.type,
                "createdAt": format_datetime(log.create_at),
            }
            for log in logs
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": (total + page_size - 1) // page_size,
    }


async def delete_log(db: AsyncSession, log_id: int) -> None:
    result = await db.execute(select(SysLog).where(SysLog.id == log_id))
    log = result.scalar_one_or_none()
    if log is None:
        raise ValueError("日志不存在")
    await db.delete(log)


async def batch_delete_log(db: AsyncSession, log_ids: list[int]) -> None:
    await db.execute(delete(SysLog).where(SysLog.id.in_(log_ids)))
