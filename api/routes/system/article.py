from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import require_permission
from models.base import format_datetime
from schemas.article import CreateArticleRequest, UpdateArticleRequest
from schemas.menu import BatchDeleteRequest
from schemas.response import ResponseModel
from services.system.article import (
    batch_delete_article,
    create_article,
    delete_article,
    get_article_by_id,
    get_article_page,
    update_article,
)

router = APIRouter(prefix="/article", tags=["文章管理"])


@router.get("/page", response_model=ResponseModel[dict[str, object]])
async def get_article_page_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    title: str | None = Query(default=None, max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/content/article/index")),
):
    """获取文章分页列表"""
    result = await get_article_page(db, page, page_size, title)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.get("/detail", response_model=ResponseModel[dict[str, object]])
async def get_article_detail(
    id: int = Query(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/content/article/view")),
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
        },
    )


@router.post("/create", response_model=ResponseModel[dict[str, object]])
async def create_article_handler(
    req: CreateArticleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/content/article/create")),
):
    """创建文章"""
    try:
        creator = current_user.name or current_user.username
        article = await create_article(db, req, creator=creator)
        return ResponseModel(
            code=200, message="创建成功", data={"id": article.id}
        )
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.put("/update/{article_id}", response_model=ResponseModel[None])
async def update_article_handler(
    article_id: PositiveInt,
    req: UpdateArticleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/content/article/update")),
):
    """更新文章"""
    try:
        updater = current_user.name or current_user.username
        await update_article(db, article_id, req, updater=updater)
        return ResponseModel(code=200, message="更新成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.delete("/{article_id}", response_model=ResponseModel[None])
async def delete_article_handler(
    article_id: PositiveInt,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/content/article/delete")),
):
    """删除文章"""
    try:
        await delete_article(db, article_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.post("/batchDelete", response_model=ResponseModel[None])
async def batch_delete_article_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/content/article/delete")),
):
    """批量删除文章"""
    try:
        await batch_delete_article(db, req.ids)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc
