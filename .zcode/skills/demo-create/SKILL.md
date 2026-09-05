---
name: demo-create
description: 生成或修改增删改查(CRUD)模块时必须使用本skill。当用户要求新增业务模块、生成增删改查接口、创建xxx管理功能、或修改现有CRUD代码时，按本skill规定的文件结构、命名和接口契约生成，保证与项目现有格式一致。适用范围：新建 Model/Schema/Service/Route、批量删除、状态切换、分页过滤等。
---

# demo-create：fastApi 项目 CRUD 模块生成规范

为 `south-admin-fastApi`（FastAPI + SQLAlchemy async + MySQL）生成增删改查模块时，**必须**按本文件的结构和契约执行。以模块名 `{{name}}`（表 `sys_{{name}}`）为例。

## 一、要创建/修改的文件（共 5 处）

| 文件 | 作用 |
|---|---|
| `models/system/{{name}}.py` | SQLAlchemy 模型（表名 `sys_{{name}}`） |
| `schemas/{{name}}.py` | Pydantic 请求/响应模型（继承 CamelModel） |
| `services/system/{{name}}.py` | 服务层（业务与数据库操作） |
| `api/routes/system/{{name}}.py` | 路由层 |
| `core/router.py` + `database/init.sql` | 注册路由 + 菜单权限种子数据 |

## 二、接口契约（与 react-admin 前端对齐，违反即为 bug）

1. **响应结构**：一律 `ResponseModel(code=200, message="...", data=...)`；业务失败抛 `HTTPException(status_code=200, detail="原因")`（由异常中间件转成统一响应体），不要返回 4xx/5xx HTTP 码。
2. **分页参数别名是 `pageSize`**：
   ```python
   page: int = 1,
   page_size: int = Query(default=10, alias="pageSize"),
   ```
   禁止裸写 `page_size: int = 10`（前端发的是 pageSize，会永远拿到默认值）。
3. **分页返回**：`{"items": ..., "page": page, "pageSize": page_size, "total": total, "totalPages": ...}`。
4. **JSON 字段驼峰**：请求/响应模型必须继承 `schemas/base.py` 的 `CamelModel`（alias_generator=to_camel），时间字段输出用 `models/base.py` 的 `format_datetime()` 转 `"YYYY-MM-DD HH:mm:ss"` 字符串。
5. **零值合法**：`state=0/status=0` 是有效值。过滤/更新判断用 `is not None`，禁止用 `if data.state:`（0 会被当成"未传"）。
6. **更新语义**：非空 rule 类字段 → 复用/新建；显式传 null/空 → 解除关联或清空（参照 `services/system/menu.py` 的 update_menu 注释块）。
7. **接口面**（依赖 `get_current_user` 鉴权）：
   `GET /page`、`GET /detail`、`POST /create`、`PUT /update/{id}`、`DELETE /{id}`、`POST /batchDelete`、（有状态时）`PUT /changeState`、`GET /list`。
8. **过滤参数**：模糊匹配 `LIKE %xx%`，参数名与前端搜索框一致；total 跟随过滤。
9. **不泄露密码**：响应不得包含 password 哈希。
10. **软删除**：`is_deleted=1` + `deleted_at`；批量删除空 ids 报"请选择要删除的xx"。

## 三、文件模板

### 1. `models/system/{{name}}.py`

```python
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Sys{{Name}}(Base):
    __tablename__ = "sys_{{name}}"

    # TODO: 业务字段，驼峰键由 Schema 层负责，这里用 snake_case 列名
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态 1=启用 0=禁用")

    # Base 已含 id/create_at/update_at/is_deleted/deleted_at，勿重复声明
```

### 2. `schemas/{{name}}.py`

```python
from typing import Optional, List
from schemas.base import CamelModel


class Create{{Name}}Request(CamelModel):
    # TODO: 业务字段；可空字段用 Optional 并给默认值
    name: str
    description: Optional[str] = None


class Update{{Name}}Request(CamelModel):
    # 更新字段全部 Optional，支持置零/清空（前端总是提交完整表单）
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class BatchDeleteRequest(CamelModel):
    ids: List[int]


class Change{{Name}}StateRequest(CamelModel):
    id: int
    state: int  # 0 隐藏 / 1 显示，零值合法不加约束
```

### 3. `services/system/{{name}}.py`

参照 `services/system/permission.py` / `menu.py`：函数签名第一个参数是 `db: AsyncSession`；分页先 `count` 再 `offset/limit`；过滤条件同时作用于 count 与 select；软删用 `update().values(is_deleted=1, deleted_at=datetime.now())`。

### 4. `api/routes/system/{{name}}.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.async_session import AsyncSession  # 以现有文件 import 为准

from config.database import get_db
from schemas.response import ResponseModel
from middleware.auth import get_current_user

router = APIRouter(prefix="/{{name}}", tags=["{{标签}}"])


@router.get("/page", response_model=ResponseModel)
async def get_{{name}}_page(
    page: int = 1,
    page_size: int = Query(default=10, alias="pageSize"),
    # TODO: 过滤参数
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ...
```

其余端点按第二节接口面补全，风格与 `api/routes/system/permission.py` 保持一致（try/except ValueError → HTTPException(200, detail)）。

### 5. 注册与种子数据

- `core/router.py`：`system_router.include_router({{name}}.router)`（并加 import）
- `database/init.sql`：参照"日志管理"三件套追加权限（`/{{authority_prefix}}/{{name}}` + index/create/update/view/delete）、菜单（type=2/3）、`sys_role_menu` 授权。

## 四、完成前自查

- [ ] `uv run python -c "import api.routes.system.{{name}}"`（或启动服务）无报错
- [ ] curl 验证：`?pageSize=20` 生效、过滤生效、create/update/delete/batchDelete 正常
- [ ] 响应 JSON 键为驼峰、时间为 `format_datetime` 字符串
