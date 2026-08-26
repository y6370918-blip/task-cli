import pytest
from sqlalchemy.orm import Session

from task_cli.exceptions import TaskNotFoundError
from task_cli.models import User
from task_cli.schemas import TaskCreate, TaskUpdate
from task_cli.services import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
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


def test_get_missing_task_raises_task_not_found(
    db_session: Session,
    user: User,
) -> None:
    with pytest.raises(TaskNotFoundError) as exc_info:
        get_task(
            db_session,
            task_id=999,
            owner_id=user.id,
        )

    assert exc_info.value.task_id == 999


def test_update_missing_task_raises_task_not_found(
    db_session: Session,
    user: User,
) -> None:
    data = TaskUpdate(
        status="done",
    )

    with pytest.raises(TaskNotFoundError) as exc_info:
        update_task(
            db_session,
            task_id=999,
            data=data,
            owner_id=user.id,
        )

    assert exc_info.value.task_id == 999


def test_delete_missing_task_raises_task_not_found(
    db_session: Session,
    user: User,
) -> None:
    with pytest.raises(TaskNotFoundError) as exc_info:
        delete_task(
            db_session,
            task_id=999,
            owner_id=user.id,
        )

    assert exc_info.value.task_id == 999


def test_delete_task_returns_none_on_success(
    db_session: Session,
    user: User,
) -> None:
    task = create_task(
        db_session,
        TaskCreate(
            title="待删除任务",
        ),
        user.id,
    )

    result = delete_task(
        db_session,
        task_id=task.id,
        owner_id=user.id,
    )

    assert result is None

    with pytest.raises(TaskNotFoundError):
        get_task(
            db_session,
            task_id=task.id,
            owner_id=user.id,
        )


def test_list_tasks_filters_by_status(
    db_session: Session,
    user: User,
) -> None:
    pending_task = create_task(
        db_session,
        TaskCreate(
            title="待处理任务",
        ),
        user.id,
    )
    done_task = create_task(
        db_session,
        TaskCreate(
            title="已完成任务",
        ),
        user.id,
    )

    done_task.status = "done"
    db_session.commit()

    tasks = list_tasks(
        db_session,
        owner_id=user.id,
        status="done",
    )

    assert [task.id for task in tasks] == [done_task.id]

    assert pending_task.id not in {task.id for task in tasks}


def test_list_tasks_applies_ordered_pagination(
    db_session: Session,
    user: User,
) -> None:
    created_tasks = [
        create_task(
            db_session,
            TaskCreate(
                title=f"任务 {number}",
            ),
            user.id,
        )
        for number in range(1, 6)
    ]

    tasks = list_tasks(
        db_session,
        owner_id=user.id,
        limit=2,
        offset=2,
    )

    assert [task.id for task in tasks] == [
        created_tasks[2].id,
        created_tasks[3].id,
    ]


def test_list_tasks_filters_owner_before_pagination(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    first_user_task = create_task(
        db_session,
        TaskCreate(
            title="当前用户任务 1",
        ),
        user.id,
    )
    create_task(
        db_session,
        TaskCreate(
            title="其他用户任务 1",
        ),
        other_user.id,
    )
    second_user_task = create_task(
        db_session,
        TaskCreate(
            title="当前用户任务 2",
        ),
        user.id,
    )
    create_task(
        db_session,
        TaskCreate(
            title="其他用户任务 2",
        ),
        other_user.id,
    )
    third_user_task = create_task(
        db_session,
        TaskCreate(
            title="当前用户任务 3",
        ),
        user.id,
    )

    tasks = list_tasks(
        db_session,
        owner_id=user.id,
        limit=2,
        offset=1,
    )

    assert first_user_task.id not in {task.id for task in tasks}

    assert [task.id for task in tasks] == [
        second_user_task.id,
        third_user_task.id,
    ]


def test_create_task_with_priority(
    db_session: Session,
    user: User,
) -> None:
    task = create_task(
        db_session,
        TaskCreate(
            title="高优先级任务",
            priority="high",
        ),
        user.id,
    )

    assert task.priority == "high"


def test_update_task_priority(
    db_session: Session,
    user: User,
) -> None:
    task = create_task(
        db_session,
        TaskCreate(
            title="需要调整优先级",
        ),
        user.id,
    )

    updated_task = update_task(
        db_session,
        task_id=task.id,
        data=TaskUpdate(
            priority="high",
        ),
        owner_id=user.id,
    )

    assert updated_task.id == task.id
    assert updated_task.priority == "high"
    assert updated_task.owner_id == user.id
