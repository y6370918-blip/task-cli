# Task CLI

一个基于 Python 的命令行任务管理工具。

## Features

- 创建任务
- 查看任务
- 更新任务状态
- 删除任务
- SQLite 数据持久化
- Pydantic 数据校验
- SQLAlchemy ORM
- 自动化测试

## Tech Stack

- Python 3.12
- Pydantic
- SQLAlchemy
- SQLite
- pytest

## Installation

创建虚拟环境：

```bash
python -m venv .venv
安装依赖：
pip install -e .
Run
task
或者：
python -m task_cli.main
Test
pytest
Project Structure
src/
└── task_cli/
    ├── main.py
    ├── cli.py
    ├── services.py
    ├── models.py
    ├── schemas.py
    ├── database.py
    ├── config.py
    └── logger.py

---
```
