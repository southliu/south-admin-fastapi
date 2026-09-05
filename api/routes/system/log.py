from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from services.system.log import create_log, get_log_page, delete_log, batch_delete_log
from schemas.response import ResponseModel
from schemas.log import CreateLogRequest
from schemas.menu import BatchDeleteRequest
from middleware.auth import get_current_user

router = APIRouter(prefix="/log", tags=["日志"])


@router.post("/create", response_model=ResponseModel)
async def create_log_handler(
    req: CreateLogRequest,
    db: AsyncSession = Depends(get_db)
):
    """创建日志"""
    try:
        await create_log(db, req)
        return ResponseModel(code=200, message="创建成功")
    except Exception as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.get("/page", response_model=ResponseModel)
async def get_log_page_list(
    page: int = 1,
    page_size: int = Query(default=10, alias="pageSize"),
    username: Optional[str] = None,
    type: int = -1,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取日志分页列表"""
    result = await get_log_page(db, page, page_size, username, type)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.delete("/{log_id}", response_model=ResponseModel)
async def delete_log_handler(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """删除日志"""
    try:
        await delete_log(db, log_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))


@router.post("/batchDelete", response_model=ResponseModel)
async def batch_delete_log_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """批量删除日志"""
    try:
        await batch_delete_log(db, req.ids)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e))
