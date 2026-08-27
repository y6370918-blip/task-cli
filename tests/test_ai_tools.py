import json

import pytest
from sqlalchemy.orm import Session

from task_cli.ai_exceptions import AIToolError
from task_cli.ai_tools import TOOLS, execute_tool
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

    assert result["task"]["priority"] == "medium"


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


def test_list_tasks_tool_declares_priority_enum() -> None:
    list_tasks_tool = next(
        tool for tool in TOOLS if tool["function"]["name"] == "list_tasks"
    )

    priority_schema = list_tasks_tool["function"]["parameters"]["properties"][
        "priority"
    ]

    assert priority_schema["enum"] == [
        "low",
        "medium",
        "high",
    ]


def test_ai_tool_list_tasks_filters_by_priority(
    db_session: Session,
    user: User,
    other_user: User,
    task: Task,
) -> None:
    task.priority = "high"

    medium_task = Task(
        title="当前用户普通任务",
        description=None,
        status="pending",
        priority="medium",
        owner_id=user.id,
    )

    other_user_task = Task(
        title="其他用户高优先级任务",
        description=None,
        status="pending",
        priority="high",
        owner_id=other_user.id,
    )

    db_session.add_all(
        [
            medium_task,
            other_user_task,
        ]
    )
    db_session.commit()

    raw_result = execute_tool(
        name="list_tasks",
        arguments={
            "priority": "high",
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == task.id
    assert result["tasks"][0]["priority"] == "high"


def test_ai_tool_list_tasks_rejects_invalid_priority(
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
                "priority": "urgent",
            },
            db=db_session,
            owner_id=user.id,
        )


def test_ai_tool_create_task_with_priority(
    db_session: Session,
    user: User,
) -> None:
    raw_result = execute_tool(
        name="create_task",
        arguments={
            "title": "高优先级任务",
            "priority": "high",
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True
    assert result["task"]["priority"] == "high"


def test_ai_tool_update_task_priority(
    db_session: Session,
    user: User,
    task: Task,
) -> None:
    raw_result = execute_tool(
        name="update_task",
        arguments={
            "task_id": task.id,
            "priority": "high",
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True
    assert result["task"]["id"] == task.id
    assert result["task"]["priority"] == "high"

    db_session.refresh(task)
    assert task.priority == "high"


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        (
            "create_task",
            {
                "title": "非法任务",
                "priority": "urgent",
            },
        ),
        (
            "update_task",
            {
                "task_id": 1,
                "priority": "urgent",
            },
        ),
    ],
)
def test_ai_write_tools_reject_invalid_priority(
    name: str,
    arguments: dict,
    db_session: Session,
    user: User,
) -> None:
    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name=name,
            arguments=arguments,
            db=db_session,
            owner_id=user.id,
        )


def test_ai_update_tool_rejects_owner_id(
    db_session: Session,
    user: User,
) -> None:
    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name="update_task",
            arguments={
                "task_id": 1,
                "owner_id": 999,
                "priority": "high",
            },
            db=db_session,
            owner_id=user.id,
        )


def test_ai_update_tool_requires_update_fields(
    db_session: Session,
    user: User,
) -> None:
    with pytest.raises(
        AIToolError,
        match="没有提供需要修改的任务字段",
    ):
        execute_tool(
            name="update_task",
            arguments={
                "task_id": 1,
            },
            db=db_session,
            owner_id=user.id,
        )


@pytest.mark.parametrize(
    "tool_name",
    [
        "create_task",
        "update_task",
    ],
)
def test_ai_write_tools_declare_priority_enum(
    tool_name: str,
) -> None:
    tool = next(item for item in TOOLS if item["function"]["name"] == tool_name)

    priority_schema = tool["function"]["parameters"]["properties"]["priority"]

    assert priority_schema["enum"] == [
        "low",
        "medium",
        "high",
    ]


def test_ai_create_tool_rejects_owner_id(
    db_session: Session,
    user: User,
) -> None:
    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name="create_task",
            arguments={
                "title": "非法归属任务",
                "priority": "high",
                "owner_id": 999,
            },
            db=db_session,
            owner_id=user.id,
        )
