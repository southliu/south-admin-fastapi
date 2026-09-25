from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常处理：响应体改为 {code, message} 格式"""
    # 业务异常（status_code=200）统一返回 code=500
    code = exc.status_code if exc.status_code >= 400 else 500
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": exc.detail},
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验异常处理：响应体改为 {code, message} 格式"""
    message = "; ".join(
        f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg', '')}"
        for err in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": f"参数校验失败: {message}"},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """未捕获异常处理：响应体改为 {code, message} 格式

    原始异常文本不返回给前端；traceback 仍会由 uvicorn 记录
    （Starlette 的 500 兜底处理器在发送响应后会重新抛出异常）。
    """
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "网络异常，请稍后重试"},
    )
