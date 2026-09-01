from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.router import api_router
from core.database import create_tables
from middleware.log import LogMiddleware
from middleware.auth import AuthError, auth_error_handler
from middleware.readonly import ReadOnlyMiddleware
from middleware.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建数据库表
    await create_tables()
    yield


app = FastAPI(title="South Admin API", version="0.1.0", lifespan=lifespan)

# 注册认证异常处理器
app.add_exception_handler(AuthError, auth_error_handler)

# 注册全局异常处理器，去掉默认的 {detail: xxx}，统一为 {code, message} 格式
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# 注册日志中间件
app.add_middleware(LogMiddleware)

# 注册只读模式中间件（readonly.enabled 为 1 时拦截除登录外的非 GET 请求）
app.add_middleware(ReadOnlyMiddleware)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(api_router)
