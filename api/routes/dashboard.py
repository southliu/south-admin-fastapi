from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from schemas.response import ResponseModel
from middleware.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("", response_model=ResponseModel)
async def get_data_trends(
    pay_date: Optional[List[str]] = Query(default=None, alias="pay_date[]"),
    current_user=Depends(get_current_user),
):
    """获取数据总览数据"""
    return ResponseModel(code=200, message="获取成功", data=[])
