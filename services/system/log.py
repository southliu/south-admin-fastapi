from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import format_datetime
from models.system.log import SysLog
from schemas.log import CreateLogRequest
from utils.audit import sanitize_params, sanitize_url


async def create_log(db: AsyncSession, data: CreateLogRequest) -> SysLog:
    """创建日志"""
    log = SysLog(
        username=data.username,
        method=data.method,
        url=sanitize_url(data.url),
        params=sanitize_params(data.params),
        user_agent=data.user_agent,
        status=data.status,
        error=data.error,
        latency=data.latency,
        type=data.type,
    )

    db.add(log)
    await db.flush()
    return log


async def get_log_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    username: str | None = None,
    log_type: int = -1,
) -> dict[str, Any]:
    """获取日志分页列表"""
    query = select(SysLog)

    if username:
        query = query.where(SysLog.username.like(f"%{username}%"))
    if log_type >= 0:
        query = query.where(SysLog.type == log_type)

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = (
        query.offset(offset).limit(page_size).order_by(SysLog.create_at.desc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    # 构建返回数据
    items = []
    for log in logs:
        items.append(
            {
                "id": log.id,
                "username": log.username,
                "method": log.method,
                "url": log.url,
                "status": log.status,
                "error": log.error,
                "latency": log.latency,
                "type": log.type,
                "createdAt": format_datetime(log.create_at),
            }
        )

    total_pages = total // page_size
    if total % page_size > 0:
        total_pages += 1

    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": total_pages,
    }


async def delete_log(db: AsyncSession, log_id: int) -> None:
    """删除日志"""
    result = await db.execute(select(SysLog).where(SysLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise ValueError("日志不存在")

    await db.delete(log)
    await db.flush()


async def batch_delete_log(db: AsyncSession, log_ids: list[int]) -> None:
    """批量删除日志"""
    if not log_ids:
        raise ValueError("请选择要删除的日志")
    await db.execute(delete(SysLog).where(SysLog.id.in_(log_ids)))
    await db.flush()
