from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth import get_current_user, require_permission
from models.system.user import SysUser
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


@router.post("/create", response_model=ResponseModel)
async def create_log_handler(
    req: CreateLogRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(get_current_user),
) -> ResponseModel:
    """创建日志"""
    try:
        req.username = current_user.username
        req.type = 3
        req.status = "error"
        req.error = "客户端错误" if req.error else None
        await create_log(db, req)
        return ResponseModel(code=200, message="创建成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.get("/page", response_model=ResponseModel)
async def get_log_page_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, alias="pageSize", ge=1, le=200),
    username: str | None = None,
    type: int = -1,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/log/index", "/authority/log")
    ),
) -> ResponseModel:
    """获取日志分页列表"""
    result = await get_log_page(db, page, page_size, username, type)
    return ResponseModel(code=200, message="获取成功", data=result)


@router.delete("/{log_id}", response_model=ResponseModel)
async def delete_log_handler(
    log_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/log/delete")
    ),
) -> ResponseModel:
    """删除日志"""
    try:
        await delete_log(db, log_id)
        return ResponseModel(code=200, message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e


@router.post("/batchDelete", response_model=ResponseModel)
async def batch_delete_log_handler(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: SysUser = Depends(
        require_permission("/authority/log/delete")
    ),
) -> ResponseModel:
    """批量删除日志"""
    try:
        await batch_delete_log(db, req.ids)
        return ResponseModel(code=200, message="批量删除成功")
    except ValueError as e:
        raise HTTPException(status_code=200, detail=str(e)) from e
