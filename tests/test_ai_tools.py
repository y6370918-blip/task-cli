import json

import pytest
from sqlalchemy.orm import Session

from task_cli.ai_exceptions import AIToolError
from task_cli.ai_tools import execute_tool
from task_cli.models import Task, User


def test_ai_tool_create_task(
    db_session: Session,
    user: User,
) -> None:

    raw_result = execute_tool(
        name="create_task",
        arguments={
            "title": "学习 pytest",
            "description": "完成 Day23",
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True

    assert result["action"] == "create_task"

    assert result["task"]["title"] == "学习 pytest"


def test_ai_tool_request_delete(
    db_session: Session,
    user: User,
) -> None:

    task = Task(
        title="待删除任务",
        description=None,
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    raw_result = execute_tool(
        name="request_delete_task",
        arguments={
            "task_id": task.id,
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True

    assert result["requires_confirmation"] is True

    assert result["action"] == "delete_task"

    assert result["confirmation_id"] is not None

    saved_task = db_session.get(
        Task,
        task.id,
    )

    assert saved_task is not None


def test_ai_tool_list_tasks_rejects_invalid_status(
    db_session: Session,
    user: User,
) -> None:

    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name="list_tasks",
            arguments={
                "status": "finished",
            },
            db=db_session,
            owner_id=user.id,
        )


def test_ai_tool_delete_rejects_non_positive_task_id(
    db_session: Session,
    user: User,
) -> None:

    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name="request_delete_task",
            arguments={
                "task_id": 0,
            },
            db=db_session,
            owner_id=user.id,
        )


def test_ai_tool_delete_requires_task_id(
    db_session: Session,
    user: User,
) -> None:

    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name="request_delete_task",
            arguments={},
            db=db_session,
            owner_id=user.id,
        )


def test_ai_tool_delete_rejects_extra_fields(
    db_session: Session,
    user: User,
) -> None:

    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name="request_delete_task",
            arguments={
                "task_id": 5,
                "owner_id": 999,
            },
            db=db_session,
            owner_id=user.id,
        )


def test_ai_tool_list_tasks_accepts_valid_status(
    db_session: Session,
    user: User,
    task: Task,
) -> None:

    raw_result = execute_tool(
        name="list_tasks",
        arguments={
            "status": task.status,
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == task.id
