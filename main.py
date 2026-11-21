from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.database import AsyncSessionLocal, async_engine, get_db
from config.settings import settings
from core.router import api_router
from middleware.auth import (
    AuthError,
    ForbiddenError,
    auth_error_handler,
    forbidden_error_handler,
)
from middleware.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from middleware.log import LogMiddleware
from middleware.readonly import ReadOnlyMiddleware
from services.system.log import purge_expired_logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal.begin() as session:
        await purge_expired_logs(session, settings.log.retention_days)
    yield
    await async_engine.dispose()


app = FastAPI(title="South Admin API", version="0.1.0", lifespan=lifespan)

# 注册认证异常处理器
app.add_exception_handler(AuthError, auth_error_handler)
app.add_exception_handler(ForbiddenError, forbidden_error_handler)

# 注册全局异常处理器，统一返回 {code, message} 格式
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# readonly.enabled 为 1 时拦截除登录外的非 GET 请求
app.add_middleware(ReadOnlyMiddleware)

# Starlette 后添加的中间件位于外层，确保只读拒绝也会写入操作日志。
app.add_middleware(LogMiddleware)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health", include_in_schema=False)
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(api_router)
