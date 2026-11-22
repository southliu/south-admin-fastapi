# South Admin FastAPI

South Admin FastAPI 后台管理系统，基于 FastAPI + SQLAlchemy + MySQL。

## 项目结构

```
south-admin-fastApi/
├── api/
│   └── routes/
│       └── system/
│           ├── user.py          # 用户接口
│           ├── role.py          # 角色接口
│           ├── menu.py          # 菜单接口
│           ├── permission.py    # 权限接口
│           └── log.py           # 日志接口
├── config/
│   ├── database.py              # 数据库配置
│   └── settings.py              # 应用配置
├── core/
│   ├── database.py              # 数据库初始化
│   └── router.py                # 路由注册
├── services/
│   ├── user.py                  # 用户服务
│   ├── role.py                  # 角色服务
│   ├── menu.py                  # 菜单服务
│   ├── permission.py            # 权限服务
│   └── log.py                   # 日志服务
├── middleware/
│   └── auth.py                  # JWT 认证中间件
├── models/
│   ├── base.py                  # 基础模型
│   └── system/
│       ├── user.py              # 用户模型
│       ├── role.py              # 角色模型
│       ├── menu.py              # 菜单模型
│       ├── permission.py        # 权限模型
│       └── log.py               # 日志模型
├── schemas/
│   ├── response.py              # 响应模型
│   ├── user.py                  # 用户 Schema
│   ├── role.py                  # 角色 Schema
│   ├── menu.py                  # 菜单 Schema
│   ├── permission.py            # 权限 Schema
│   └── log.py                   # 日志 Schema
├── utils/
│   └── security.py              # 安全工具
├── main.py                      # 应用入口
├── pyproject.toml               # 项目配置
├── docker-compose.yaml          # Docker Compose 部署配置
├── config.yaml                  # 应用配置（不入库）
└── config.yaml.example          # 配置文件示例
```

## 快速开始

### 1. 安装依赖

```bash
pip install uv
uv sync
```

### 2. 配置应用

复制 `config.yaml.example` 为 `config.yaml`，并修改数据库和 JWT 配置：

```bash
cp config.yaml.example config.yaml
```

配置文件格式：

```yaml
database:
  url: "mysql+aiomysql://root:your_password@localhost:3306/south_admin?charset=utf8mb4"

jwt:
  secret_key: "your-secret-key-here"
  algorithm: "HS256"
  access_token_expire_minutes: 1440
```

### 3. 启动服务

```bash
uv run uvicorn main:app --reload
```

### 4. 导入数据库数据

```bash
docker cp database/init.sql admin:/tmp/init.sql
docker exec admin bash -c "mysql -u root -p'your_password' --default-character-set=utf8mb4 south_admin < /tmp/init.sql"
```

### 5. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 认证方式

使用 JWT Bearer Token 认证，在请求头中添加：

```
Authorization: Bearer <token>
```

## 部署操作

### 0. 准备 Docker Compose

服务器需安装 Docker 和 Compose 插件，确认以下命令可用：

```bash
docker compose version
```

### 1. 本地构建镜像

```shell
docker build -t south-admin-fastapi:v1 .
# 本地导出镜像文件
docker save south-admin-fastapi:v1 -o south-admin-fastapi-v1.tar.gz
```

### 2. 服务器加载镜像

将镜像文件上传到服务器 `/home/`，然后加载：

```bash
docker load -i /home/south-admin-fastapi-v1.tar.gz
docker images | grep south-admin-fastapi
```

### 3. 准备配置文件和网络

将本仓库的 `docker-compose.yaml` 上传到服务器 `/home/south-admin-fastApi/`。
确保 `/home/south-admin-fastApi/config.yaml` 已存在且为文件；首次部署时参考
`config.yaml.example` 填写数据库和 JWT 配置，已有配置继续使用。

Compose 保留原有容器名、镜像、自动重启策略、`9000:9000` 端口映射及配置文件挂载路径。
`app-net` 使用现有外部网络，Compose 不负责创建或删除它；若网络尚不存在，先执行：

```bash
docker network create app-net
```

### 4. 启动服务

如果之前通过 `docker run` 创建过同名容器，首次切换 Compose 时先停止并删除旧容器：

```bash
docker stop south-admin-fastapi
docker rm south-admin-fastapi
```

在部署目录校验配置并后台启动：

```bash
cd /home/south-admin-fastApi
test -f config.yaml
docker compose config --quiet
docker compose up -d

# 查看容器状态和日志
docker compose ps
docker compose logs --tail=100 south-admin-fastapi

# 校验服务
curl http://127.0.0.1:9000/
```

部署后的接口文档地址为 `http://服务器地址:9000/docs`。

### 5. 更新与日常管理

更新时重新构建、导出并加载镜像，再在部署目录执行 `docker compose up -d`。
修改 `config.yaml` 后执行 `docker compose restart south-admin-fastapi`。

```bash
# 实时查看日志
docker compose logs -f south-admin-fastapi

# 停止并删除 Compose 容器，保留外部 app-net 网络和宿主机配置文件
docker compose down
```

### 6. 配置 Nginx

如果 Nginx 容器也在 `app-net` 网络中，上游地址使用 `south-admin-fastapi:9000`。
容器内服务与宿主机映射端口均为 `9000`。

```bash
vim /home/nginx/conf.d/default.conf
docker exec nginx-app nginx -t
docker exec nginx-app nginx -s reload
```

## 后端运行约定

- 管理接口按操作权限校验。系统模块沿用前端的 `/authority/{模块}/{操作}`，同时兼容 `/system/{模块}/{操作}`；详情支持 `view` 和 `detail`。拥有有效 `admin` 角色的用户可管理全部模块，权限记录的增删改仅允许管理员操作。
- 普通管理用户只能分配自己持有的角色、菜单及权限规则，不能修改管理员账号或管理员角色。禁用账号后，其已有 Token 也无法继续访问受保护接口。
- 请求数据库事务在响应发送前统一提交；业务失败、参数错误和数据库异常会回滚。直接调用 services 的维护脚本需自行使用 `async with AsyncSessionLocal.begin()` 管理事务。
- 密码加密和校验为异步函数，调用时需要 `await`；bcrypt 密码上限为 UTF-8 编码后的 72 字节。
- 分页参数要求 `page >= 1`、`1 <= pageSize <= 200`。菜单 `/page` 返回完整匹配树，不按节点截断；`total` 为匹配节点数，`items` 额外保留这些节点的祖先以便展示。
- 用户姓名、邮箱、手机及角色、权限描述在 PUT 更新时，不传、`null` 或空字符串均清空。
- 前端错误日志上报仅需登录，后端固定使用当前用户名和前端错误类型，忽略客户端伪造的身份与状态。
- 操作日志复用请求中的鉴权结果，密码、Token、密钥、手机和邮箱字段会递归脱敏；URL 不保存查询参数，参数最多采集 16 KiB，非 JSON 请求体不保存。HTTP 200 的业务失败也记录为失败。
- 数据库默认关闭 SQL 回显并隐藏查询参数；Docker 直接使用构建时安装的虚拟环境启动，不在启动时同步开发依赖。

运行回归检查：

```bash
uv run python -m unittest discover -s tests -v
```
