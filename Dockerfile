FROM python:3.14

# 安装uv依赖管理器
RUN pip install uv

WORKDIR /app

# 先拷贝依赖锁定文件，利用Docker缓存
COPY pyproject.toml uv.lock ./

# 安装生产依赖
RUN uv sync --frozen --no-dev

# 拷贝全部项目源码
COPY . .

# 暴露端口
EXPOSE 9000

# 启动服务
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
