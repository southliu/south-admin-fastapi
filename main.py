import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.database import async_engine, sync_engine
from core.database import create_tables
from core.router import api_router
from middleware.auth import (
    AuthError,
    PermissionDeniedError,
    auth_error_handler,
    permission_error_handler,
)
from middleware.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from middleware.log import LogMiddleware
from middleware.readonly import ReadOnlyMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动时创建数据库表
    await create_tables()
    try:
        yield
    finally:
        await async_engine.dispose()
        await asyncio.to_thread(sync_engine.dispose)


app = FastAPI(title="South Admin API", version="0.1.0", lifespan=lifespan)

# 注册认证异常处理器
app.add_exception_handler(AuthError, auth_error_handler)
app.add_exception_handler(PermissionDeniedError, permission_error_handler)

# 全局异常统一为 {code, message} 格式。
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# 日志位于最外层，以便记录只读模式拒绝的请求。
app.add_middleware(ReadOnlyMiddleware)
app.add_middleware(LogMiddleware)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


app.include_router(api_router)
