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

### 0. 安装docker版本的python，已安装可跳过

```shell
docker pull python:3.14
```

### 1. 本地构建镜像

```shell
docker build -t south-admin-fastapi:v1 .
# 本地导出为压缩包（约 450MB）
docker save south-admin-fastapi:v1 -o south-admin-fastapi-v1.tar.gz
```

### 2. 服务器加载镜像

```shell
# 先停止运行中的容器（崩溃重启的也一样执行）
docker stop south-admin-fastapi
docker rm south-admin-fastapi
# 再删除旧容器
docker rmi south-admin-fastapi:v1

# 2. 构建新镜像
docker load -i /home/south-admin-fastapi-v1.tar.gz
docker images | grep south-admin-fastapi

# 3. 前台临时启动验证（确认不再报config.yaml缺失）
docker run -d \
--name south-admin-fastapi \
--restart always \
--network app-net \
-p 9000:9000 \
-v /home/south-admin-fastApi/config.yaml:/app/config.yaml \
south-admin-fastapi:v1


# 校验
curl 127.0.0.1:9000

# 查看日志
docker logs south-admin-fastapi

# 编辑nginx配置，调整端口指向，xxx:8000，9000端口启动也是使用8000端口，xxx变化
vim /home/nginx/conf.d/default.conf
docker exec nginx-app nginx -t
docker exec nginx-app nginx -s reload
```
