from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.system.article import SysArticle
from models.base import format_datetime
from schemas.article import CreateArticleRequest, UpdateArticleRequest


async def get_article_by_id(db: AsyncSession, article_id: int) -> Optional[SysArticle]:
    """根据ID查询文章"""
    result = await db.execute(
        select(SysArticle)
        .where(and_(SysArticle.id == article_id, SysArticle.is_deleted == 0))
    )
    return result.scalar_one_or_none()


async def get_article_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    title: Optional[str] = None
) -> dict:
    """获取文章分页列表"""
    query = select(SysArticle).where(SysArticle.is_deleted == 0)

    if title:
        query = query.where(SysArticle.title.like(f"%{title}%"))

    # 查询总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(SysArticle.create_at.desc())
    result = await db.execute(query)
    articles = result.scalars().all()

    # 构建返回数据
    items = []
    for article in articles:
        items.append({
            "id": article.id,
            "title": article.title,
            "author": article.author,
            "content": article.content,
            "creator": article.creator,
            "updater": article.updater,
            "createdAt": format_datetime(article.create_at),
            "updatedAt": format_datetime(article.update_at),
        })

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


async def create_article(db: AsyncSession, data: CreateArticleRequest, creator: Optional[str] = None) -> SysArticle:
    """创建文章"""
    article = SysArticle(
        title=data.title,
        author=data.author or None,
        content=data.content or None,
        demo=data.demo,
        creator=creator,
    )

    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


async def update_article(db: AsyncSession, article_id: int, data: UpdateArticleRequest, updater: Optional[str] = None) -> SysArticle:
    """更新文章"""
    article = await get_article_by_id(db, article_id)
    if not article:
        raise ValueError("文章不存在")

    article.title = data.title

    # 可空字段：直接赋值，前端不传或传空（null/''）即为清空
    article.author = data.author or None
    article.content = data.content or None
    article.demo = data.demo
    article.updater = updater

    await db.commit()
    await db.refresh(article)
    return article


async def delete_article(db: AsyncSession, article_id: int) -> None:
    """删除文章"""
    article = await get_article_by_id(db, article_id)
    if not article:
        raise ValueError("文章不存在")

    article.is_deleted = 1
    article.deleted_at = datetime.now()
    await db.commit()


async def batch_delete_article(db: AsyncSession, article_ids: List[int]) -> None:
    """批量删除文章"""
    if not article_ids:
        raise ValueError("请选择要删除的文章")

    result = await db.execute(
        select(SysArticle).where(
            and_(SysArticle.id.in_(article_ids), SysArticle.is_deleted == 0)
        )
    )
    articles = result.scalars().all()

    now = datetime.now()
    for article in articles:
        article.is_deleted = 1
        article.deleted_at = now

    await db.commit()
