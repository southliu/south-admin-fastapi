# South Admin FastAPI

South Admin 后台管理系统的 FastAPI 后端，使用 FastAPI、SQLAlchemy 2
异步会话、aiomysql、Pydantic v2 和 Python 3.14。依赖统一由 uv 管理。

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置应用

复制 `config.yaml.example` 为 `config.yaml`，至少修改数据库连接和 JWT
密钥。`config.yaml` 含敏感信息，不应提交到版本库。

```powershell
Copy-Item config.yaml.example config.yaml
```

配置也可由环境变量覆盖。嵌套字段使用双下划线，例如：

```powershell
$env:ENVIRONMENT = "production"
$env:DATABASE__URL = "mysql+aiomysql://user:password@db:3306/south_admin?charset=utf8mb4"
$env:JWT__SECRET_KEY = "replace-with-a-long-random-secret"
```

生产环境会拒绝示例 JWT 密钥以及长度不足 16 个字符的密钥。

### 3. 初始化数据库

Alembic 负责表结构和索引，`database/init.sql` 会重置用户、角色、权限与菜单
数据后写入基础种子，因此只应在新库初始化时执行。首次部署依次执行：

```bash
uv run alembic upgrade head
mysql --default-character-set=utf8mb4 -u root -p south_admin < database/init.sql
```

初始化脚本不包含默认管理员密码。导入种子数据后，通过环境变量创建管理员：

```powershell
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "replace-with-a-strong-password"
uv run python -m scripts.create_admin
Remove-Item Env:ADMIN_PASSWORD
```

管理员密码至少 8 个字符，且 UTF-8 编码后不得超过 bcrypt 的 72 字节上限。

### 4. 启动服务

```bash
uv run uvicorn main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 开发检查

```bash
uv run ruff format .
uv run ruff check .
uv run pytest -q
uv run alembic check
```

新增或修改 SQLAlchemy 模型后，应生成并检查迁移，再升级数据库：

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

应用启动时不会自动建表，部署必须先完成 Alembic 迁移。

## 认证与权限

受保护接口使用 Bearer Token：

```text
Authorization: Bearer <token>
```

用户被禁用、删除、退出登录或修改密码后，已签发 Token 会失效。路由同时执行
后端权限校验，不能只依赖前端菜单隐藏。

## Docker 部署

镜像默认以非 root 用户运行，监听 `9000` 端口。生产配置通过只读挂载或环境变量
提供，镜像内不包含 `config.yaml`。

```bash
docker build -t south-admin-fastapi:v1 .

docker run -d \
  --name south-admin-fastapi \
  --restart unless-stopped \
  --network app-net \
  -p 9000:9000 \
  -v /home/south-admin-fastApi/config.yaml:/app/config.yaml:ro \
  south-admin-fastapi:v1
```

上线新版本前先在相同配置下执行迁移：

```bash
docker run --rm \
  --network app-net \
  -v /home/south-admin-fastApi/config.yaml:/app/config.yaml:ro \
  south-admin-fastapi:v1 \
  alembic upgrade head
```

可使用 `docker logs south-admin-fastapi` 查看应用日志，使用
`curl --fail http://127.0.0.1:9000/health` 检查应用和数据库健康状态。
