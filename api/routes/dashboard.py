from fastapi import APIRouter, Depends, Query

from middleware.auth import require_permission
from schemas.response import ResponseModel

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("", response_model=ResponseModel[list[dict[str, object]]])
async def get_data_trends(
    pay_date: list[str] | None = Query(
        default=None,
        alias="pay_date[]",
        max_length=2,
    ),
    current_user=Depends(require_permission("/dashboard")),
):
    """获取数据总览数据"""
    return ResponseModel(code=200, message="获取成功", data=[])
