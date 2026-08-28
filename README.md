# task-cli

一个使用 FastAPI、PostgreSQL 和 DeepSeek Tool Calling 构建的 AI 任务管理 API。

项目最初是命令行任务管理器，目前已经演进为多用户 Web API。仓库名称保留为 `task-cli`，但正式产品入口是 FastAPI。

## Current Features

- 用户注册和登录
- JWT Authentication
- 用户任务数据隔离
- 创建、查询、修改和删除任务
- 状态、优先级和截止时间
- 分页与过滤
- DeepSeek Tool Calling
- AI 创建、查询和修改任务
- 删除操作人工确认
- PostgreSQL 数据持久化
- Alembic 数据库迁移
- pytest 自动化测试
- Docker Compose
- pre-commit 和 GitHub Actions

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- Alembic
- DeepSeek API
- pytest
- Docker

## Local Development

创建并启用虚拟环境，然后安装依赖：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

启动 PostgreSQL：

```powershell
docker compose up -d db
```

升级数据库：

```powershell
python -m alembic upgrade head
```

启动 API：

```powershell
uvicorn task_cli.api:app --reload
```

打开 API 文档：

```text
http://127.0.0.1:8000/docs
```

## Tests

```powershell
python -m pytest -q
```

## Docker Compose

```powershell
docker compose up -d --build
```

查看服务：

```powershell
docker compose ps
```

停止服务时不要添加 `-v`，除非确定要删除 PostgreSQL 数据：

```powershell
docker compose down
```
