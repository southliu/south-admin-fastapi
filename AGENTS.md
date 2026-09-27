# AGENTS.md

South Admin 后台管理系统的 FastAPI 后端：FastAPI + SQLAlchemy 2 (async) + aiomysql + Pydantic v2，Python 3.14，依赖由 uv 管理。


## 常用命令

```bash
uv sync                                      # 安装依赖
uv run uvicorn main:app --reload --port 8000 # 启动开发服务（main.py 无 __main__ 块，python main.py 跑不起来）
uv run ruff format .                         # 格式化 Python 代码
uv run ruff check .                          # 检查 Python 代码
```

- 接口文档：http://localhost:8000/docs
- 无测试套件；`test_main.http` 是手工调试文件。验证改动需实际启动服务或写临时脚本调用。

## Python 代码规范（必须遵守）

- 以 PEP 8 为基础，由根目录 `.editorconfig` 和 `pyproject.toml` 中的 Ruff 配置统一约束。
- 使用 4 个空格缩进，禁止 Tab 及 Tab/空格混用；代码每行不超过 79 字符，独立注释和 docstring 每行不超过 72 字符。
- 模块顶层函数和类之间空两行，类内方法之间空一行；函数内部仅在不同逻辑块之间使用单个空行。
- import 按标准库、第三方库、项目模块分组并各空一行；使用绝对导入，禁止 `from xxx import *`，禁止保留无用 import。
- 变量、函数和模块使用 `snake_case`，类使用 `PascalCase`，常量使用 `UPPER_SNAKE_CASE`，非公开名称以单下划线开头。
- 运算符两侧保留空格，括号内部不加多余空格，不保留行尾空格；字符串统一使用双引号，多行集合和调用保留尾随逗号。
- `#` 后保留一个空格；注释只解释 non-obvious reason，不复述代码，不保留被注释掉的旧代码。
- 公共函数、services 方法和复杂数据结构提供完整类型注解；使用 Python 3.14 语法（如 `list[str]`、`X | None`），避免旧式 `List`、`Optional`。
- 禁止可变默认参数、裸 `except`、静默吞异常和使用 `print()` 记录运行日志；使用具体异常和项目日志设施，不记录密码、Token、密钥或完整敏感信息。
- 条件判断使用 `is None`、`is not None` 和对象真值，不写 `== None`、`== True` 或 `len(items) == 0`。
- 函数保持单一职责并优先提前返回，避免过深嵌套；参数过多时使用已有或新增的 Pydantic schema 封装。
- `async def` 中不得调用阻塞式网络、数据库或文件 I/O；所有异步调用必须正确 `await`，数据库会话继续通过依赖注入获取。
- 所有新增或修改的 Python 文件在交付前必须执行 `uv run ruff format <files>` 和 `uv run ruff check <files>`。只修复本次涉及文件，禁止借规范接入批量重写无关历史代码。

## 架构分层（按目录分类）

```
main.py              入口：lifespan 启动时建表；注册中间件（log/readonly）与全局异常处理器
core/router.py       路由注册（新增模块需在此挂载；system 各模块挂在 /system 前缀下）
core/database.py     create_tables()：同步引擎建表，并 import 全部模型
config/settings.py   读 config.yaml：JWT 配置、readonly.enabled（READONLY_ENABLED）
config/database.py   引擎与会话：async_engine / AsyncSessionLocal / get_db（同步引擎仅用于建表）
database/init.sql    种子数据（菜单/角色/管理员）

api/routes/system/   路由层：薄处理器，Depends(get_db) + Depends(get_current_user)
                    user.py role.py menu.py permission.py log.py
services/system/     业务与数据库操作层（逻辑都写在这里）
                    user.py role.py menu.py permission.py log.py
models/system/       SQLAlchemy 模型，表名 sys_*
                    user.py role.py menu.py permission.py log.py
models/base.py       公共字段（id/create_at/update_at）+ format_datetime
schemas/base.py      CamelModel（snake_case 字段自动生成 camelCase 别名）
schemas/response.py  ResponseModel / PageData 统一响应
schemas/             其余请求/响应模型按模块分文件：user.py role.py menu.py permission.py log.py
middleware/          auth（JWT 认证）、exceptions（统一错误格式）、log（请求日志）、readonly（只读模式拦截）
utils/security.py    bcrypt 密码加密/校验、JWT 签发/解析
```

五个业务模块（user/role/menu/permission/log）在 api/routes/system、services/system、models/system、schemas 各有一份同名文件，新增模块照此对齐。

数据流向：route → services → model，不允许 route 直接写 ORM 查询或 services 绕过 model 约定。生成或修改 CRUD 模块时用 `.zcode/skills/demo-create` skill（已规定文件结构、命名与接口契约）。

## 关键约定

- **响应格式**：统一 `ResponseModel {code, message, data}`；分页用 `PageData`（items/page/pageSize/total/totalPages）。所有 Pydantic 字段 snake_case，CamelModel 自动别名成 camelCase。
- **业务异常**：services 层 `raise ValueError("中文提示")` → 路由层捕获后 `raise HTTPException(status_code=200, detail=str(e))` → 全局处理器转为 HTTP 200 + `{code: 500, message}`。不要在 services 里直接抛 HTTPException。
- **认证失败**：HTTP 200 + 响应体 `code: 401`（AuthError），前端按 code 判断。
- **只读模式**：`config.yaml` 的 `readonly.enabled: 1` 时，除 `/system/user/login` 与 GET/HEAD/OPTIONS 外的请求全部拒绝，返回 HTTP 200 + `code: 500`（ReadOnlyMiddleware）。
- **PUT 更新语义**：全量替换。nullable 字段"不传/传空（null 或 ''）"一律视为清空（见 83f9c5f、87ced1c）。前端 `filterEmptyStr` 现在会发送空字符串，与该语义配套。
- **菜单 rule 与权限联动**：rule 非空 → 复用/新建/重命名 SysPermission；清空 → 仅解除关联（permission_id = null），权限记录由权限管理独立维护。`SysPermission.name` 有 UNIQUE 约束，写入前必须查重。
- **路由命名**：`/list` `/page` `/detail` `/create` `/update/{id}` `/batchDelete` `/changeState`；分页 query 用 `Query(alias="pageSize")` 这类 camelCase 别名。
- **时间序列化**：用 `models/base.py` 的 `format_datetime` 输出 `YYYY-MM-DD HH:mm:ss` 字符串。

## 已知坑

- `config.yaml` 不入库（含密钥），只有 `config.yaml.example`；不要提交或打印其内容。
- 临时脚本直接操作数据库：用 `config.database.AsyncSessionLocal()`，且必须先 import 全部模型模块（user/role/menu/permission），否则 mapper 报 `KeyError: 'SysRole'`。
- Windows 下 aiomysql 退出时刷 "Event loop is closed" 噪音会淹没 stdout，脚本输出用 grep 过滤标记。
- 启动时 `core/database.py` 的 `create_tables()` 会自动建表；表结构改动对已有数据不生效，需要手工迁移。

## 工作规则（必须遵守）

1. 不允许跳过项目上下文直接改代码；先读相关模块再动手。
2. 不允许没有验证就声称完成；改动必须实际启动服务/脚本验证后才能报告完成。
3. 不允许为了完成局部需求大范围重构无关模块。
4. 不允许恢复或覆盖用户已有的未说明改动（改动前先 `git status`/`git diff` 确认工作区）。
5. 不允许引入与当前项目技术栈和代码风格冲突的实现方式。
6. 注释只写 non-obvious reason，禁止保留 intermediate attempts；PR/提交描述只写最终行为，diff 里看不出来的取舍与从未合入的状态一律不提。
7. 验证用的临时数据（测试用户、日志）和前后端 dev 端口在收尾时必须清理/关闭；临时改动（如前端 `.env.development` 代理切换）必须还原。
8. AI 生成或修改代码时必须遵守本文件的 Python 代码规范；不得通过扩大 `noqa`、全局 ignore 或跳过 Ruff 来掩盖本次引入的问题。
