from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from services.system.article import (
    get_article_page,
    get_article_by_id,
    create_article,
    update_article,
    delete_article,
    batch_delete_article,
)
from schemas.response import ResponseModel
from schemas.article import CreateArticleRequest, UpdateArticleRequest
from schemas.menu import BatchDeleteRequest
from middleware.auth import get_current_user
from models.base import format_datetime

router = APIRouter(prefix="/article", tags=["文章管理"])


@router.get("/page", response_model=ResponseModel)
async def get_article_page_list(
    page: int = 1,
    page_size: int = Query(default=10, alias="pageSize"),
    title: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取文章分页列表"""
    result = await get_article_page(db, page, page_size, title)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel)
async def get_article_detail(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取文章详情"""
    article = await get_article_by_id(db, id)
    if not article:
        raise HTTPException(status_code=200, detail="文章不存在")

    return ResponseModel(
        code=200,
        message="获取成功",
        data={
            "id": article.id,
            "title": article.title,
            "author": article.author,
            "content": article.content,
            "demo": article.demo,
            "creator": article.creator,
            "updater": article.updater,
            "createdAt": format_datetime(article.create_at),
            "updatedAt": format_datetime(article.update_at),
        }
    )


@router.post("/create", response_model=ResponseModel)
async def create_article_handler(
    req: CreateArticleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """创建文章"""
    try:
        creator = current_user.name or current_user.username
        article = await create_article(db, req, creator=creator)
        return ResponseModel(code=200, message="创建成功", data={"id": article.id})
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.put("/update/{article_id}", response_model=ResponseModel)
async def update_article_handler(
    article_id: int,
    req: UpdateArticleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """更新文章"""
    try:
        updater = current_user.name or current_user.username
        await update_article(db, article_id, req, updater=updater)
        return ResponseModel(code=200, message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.delete("/{article_id}", response_model=ResponseModel)
async def delete_article_handler(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """删除文章"""
    try:
        await delete_article(db, article_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.post("/batchDelete", response_model=ResponseModel)
async def batch_delete_article_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """批量删除文章"""
    try:
        await batch_delete_article(db, req.ids)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))
