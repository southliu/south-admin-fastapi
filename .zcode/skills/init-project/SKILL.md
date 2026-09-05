---
name: init-project
description: 初始化/重置本项目为纯净脚手架时必须使用。当用户要求"初始化项目"、"重置为纯净模板"、"只保留 system 和 dashboard"、"删除演示/业务模块接口"，或复制本脚手架开始新项目时触发。规定保留白名单、删除清单、路由与建表注册清理、init.sql 种子数据清理和验证步骤。
---

# init-project：重置为纯净脚手架

把模板中除 dashboard 与 system 五个权限模块（user/role/menu/permission/log）之外的业务/演示模块全部删除，恢复到可直接开发新项目的初始状态。以白名单为准：凡是白名单之外的业务模块文件一律删除，不要按"文件名是否像 demo"判断（如 article 属于业务模块，同样删除）。

## 一、执行前置

- 若目标目录是 git 仓库，先 `git status` 确认工作区状态——本 skill 大量删文件，干净的工作区才能用 git 兜底回滚；若是直接复制的模板副本（无 `.git`），跳过此步并提醒用户删除不可逆。
- 确认 `config.yaml` 存在（不入库，只有 example）；第五节的验证需要它才能导入应用。

## 二、保留白名单

| 目录 | 保留 |
|---|---|
| `api/routes/` | `dashboard.py`、`system/` 下的 user/role/menu/permission/log 五个文件 |
| `services/system/` | user/role/menu/permission/log |
| `models/system/` | user/role/menu/permission/log（`models/base.py` 保留） |
| `schemas/` | `base.py`、`response.py`、user/role/menu/permission/log |
| 其余 | `core/`、`config/`、`middleware/`、`utils/`、`main.py`、所有 `__init__.py` 全部保留 |

`__init__.py` 均为空文件，删除同目录业务文件时不需要改它们。

## 三、删除与清理（共 4 处）

1. **删模块文件**：白名单之外的业务模块文件，四个目录各一份（如 article 对应 `api/routes/system/article.py`、`services/system/article.py`、`models/system/article.py`、`schemas/article.py`）。
2. **`core/router.py`**：重写为只挂 system_router（include 五件套）与 `dashboard.router`；删除业务路由块（如 `content_router`）及其 import。
3. **`core/database.py`**：模型 import 只保留五个 Sys 模型。建表靠这里的 import 发现模型：漏删会 ImportError，漏保留会建不出表。
4. **`database/init.sql`**：种子数据收敛为"仪表盘 + 系统管理"：
   - 保留：admin/user1 两个用户与角色、`/dashboard` 与 `/authority/*` 权限、系统管理（/system）子菜单（用户/菜单/角色/日志管理）及其 type=3 按钮菜单、对应的 `sys_role_menu` 关联。
   - 删除：`/demo/*`、`/content/*`、外部链接（`/link`、ant-design 外链）等演示权限、菜单（含"组件""内容管理"顶级菜单及其整个子树）和 `sys_role_menu` 关联。
   - 顶级菜单 `order` 重新从 0 连续编号（只调顶级，子菜单/按钮的 order 不动）；`DELETE FROM sys_menu WHERE router IN (...)` 列表收敛为保留的 router。

## 四、残留检查

用实际删除的模块名（如 article）grep 全项目确认无残留，命中即清理：

```bash
grep -rni "article" --include="*.py" --include="*.sql" --include="*.md" --include="*.http" .
```

`test_main.http`、`AGENTS.md`、README 若引用了被删模块，同步清理。

## 五、验证（全部通过才能报告完成）

```bash
# 1. 应用可导入，路由只剩框架路由（/、/docs 等）+ /system/* + /dashboard
#    必须用 openapi()['paths'] 看业务路由：本项目 FastAPI 版本的 include_router 是惰性的，
#    app.routes 里业务路由是无 path 属性的 _IncludedRouter，遍历 app.routes 只会看到框架路由
uv run python -c "from main import app; print(sorted(app.openapi()['paths']))"

# 2. 启动服务无报错后关闭（Windows 下退出时 aiomysql 的 "Event loop is closed" 是已知噪音）
uv run uvicorn main:app --port 8000
```

数据库提醒：已有库不会自动删演示表（如 `sys_article`），需要的话手工 DROP；菜单数据要重放新的 init.sql 才会刷新。不改 `.git` 历史，不读不改 `config.yaml` 内容。
