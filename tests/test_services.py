from sqlalchemy.orm import Session

from task_cli.models import User
from task_cli.schemas import TaskCreate
from task_cli.services import (
    create_task,
    list_tasks,
)


# =========================================================
# 1. 测试创建任务
# =========================================================

def test_create_task(
    db_session: Session,
    user: User,
) -> None:

    data = TaskCreate(
        title="学习Service",
    )

    task = create_task(
        db_session,
        data,
        user.id,
    )

    assert task.id is not None

    assert task.title == "学习Service"

    assert task.owner_id == user.id

    assert task.status == "pending"


# =========================================================
# 2. 测试查询当前用户自己的任务
# =========================================================

def test_list_tasks(
    db_session: Session,
    user: User,
) -> None:

    create_task(
        db_session,
        TaskCreate(
            title="任务1",
        ),
        user.id,
    )

    tasks = list_tasks(
        db_session,
        user.id,
    )

    assert len(tasks) == 1

    assert tasks[0].title == "任务1"

    assert tasks[0].owner_id == user.id


# =========================================================
# 3. 测试用户之间的任务隔离
# =========================================================

def test_list_tasks_only_returns_own_tasks(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:

    # User A 的任务
    create_task(
        db_session,
        TaskCreate(
            title="TOM的任务",
        ),
        user.id,
    )

    # User B 的任务
    create_task(
        db_session,
        TaskCreate(
            title="Jerry的任务",
        ),
        other_user.id,
    )

    # User A 查询自己的任务
    tasks = list_tasks(
        db_session,
        user.id,
    )

    assert len(tasks) == 1

    assert tasks[0].title == "TOM的任务"

    assert tasks[0].owner_id == user.id