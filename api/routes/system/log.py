from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import require_permission
from schemas.log import CreateLogRequest
from schemas.menu import BatchDeleteRequest
from schemas.response import ResponseModel
from services.system.log import (
    batch_delete_log,
    create_log,
    delete_log,
    get_log_page,
)

router = APIRouter(prefix="/log", tags=["日志"])


@router.post("/create", response_model=ResponseModel[None])
async def create_log_handler(
    req: CreateLogRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/log/index")),
):
    """创建日志"""
    try:
        await create_log(db, req)
        return ResponseModel(code=200, message="创建成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.get("/page", response_model=ResponseModel[dict[str, object]])
async def get_log_page_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    username: str | None = Query(default=None, max_length=100),
    log_type: int = Query(default=-1, alias="type", ge=-1, le=3),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/log/index")),
):
    """获取日志分页列表"""
    result = await get_log_page(db, page, page_size, username, log_type)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.delete("/{log_id}", response_model=ResponseModel[None])
async def delete_log_handler(
    log_id: PositiveInt,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/log/delete")),
):
    """删除日志"""
    try:
        await delete_log(db, log_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc


@router.post("/batchDelete", response_model=ResponseModel[None])
async def batch_delete_log_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("/authority/log/delete")),
):
    """批量删除日志"""
    try:
        await batch_delete_log(db, req.ids)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as exc:
        raise HTTPException(status_code=200, detail=str(exc)) from exc
