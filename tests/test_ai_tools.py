import json
from datetime import UTC, datetime, timedelta

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


def test_ai_create_tool_declares_due_at() -> None:
    tool = next(item for item in TOOLS if item["function"]["name"] == "create_task")

    due_at_schema = tool["function"]["parameters"]["properties"]["due_at"]

    assert due_at_schema["type"] == "string"
    assert "时区" in due_at_schema["description"]


def test_ai_update_tool_declares_nullable_due_at() -> None:
    tool = next(item for item in TOOLS if item["function"]["name"] == "update_task")

    due_at_schema = tool["function"]["parameters"]["properties"]["due_at"]

    assert {
        "type": "string",
    } in due_at_schema["anyOf"]

    assert {
        "type": "null",
    } in due_at_schema["anyOf"]

    assert "时区" in due_at_schema["description"]


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


def test_ai_tool_create_task_with_due_at(
    db_session: Session,
    user: User,
) -> None:
    due_at = datetime(
        2026,
        9,
        5,
        10,
        0,
        tzinfo=UTC,
    )

    raw_result = execute_tool(
        name="create_task",
        arguments={
            "title": "AI 创建截止任务",
            "due_at": due_at.isoformat(),
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    saved_task = db_session.get(
        Task,
        result["task"]["id"],
    )

    assert saved_task is not None
    assert saved_task.due_at is not None

    # SQLite 读取时间时可能丢失 tzinfo，
    # 但这里输入的是 UTC，时间值本身不变。
    assert saved_task.due_at.replace(tzinfo=UTC) == due_at

    assert result["task"]["due_at"] == saved_task.due_at.isoformat()


def test_ai_tool_list_tasks_returns_due_at(
    db_session: Session,
    user: User,
    task: Task,
) -> None:
    task.due_at = datetime(
        2026,
        9,
        6,
        10,
        0,
        tzinfo=UTC,
    )

    db_session.commit()
    db_session.refresh(task)

    raw_result = execute_tool(
        name="list_tasks",
        arguments={},
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["tasks"][0]["id"] == task.id
    assert result["tasks"][0]["due_at"] == task.due_at.isoformat()


def test_ai_tool_update_task_due_at(
    db_session: Session,
    user: User,
    task: Task,
) -> None:
    due_at = datetime(
        2026,
        9,
        7,
        18,
        0,
        tzinfo=UTC,
    )

    raw_result = execute_tool(
        name="update_task",
        arguments={
            "task_id": task.id,
            "due_at": due_at.isoformat(),
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    db_session.refresh(task)

    assert task.due_at is not None
    assert task.due_at.replace(tzinfo=UTC) == due_at
    assert result["task"]["due_at"] == task.due_at.isoformat()


def test_ai_tool_clear_task_due_at(
    db_session: Session,
    user: User,
    task: Task,
) -> None:
    task.due_at = datetime(
        2026,
        9,
        8,
        10,
        0,
        tzinfo=UTC,
    )

    db_session.commit()

    raw_result = execute_tool(
        name="update_task",
        arguments={
            "task_id": task.id,
            "due_at": None,
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    db_session.refresh(task)

    assert task.due_at is None
    assert result["task"]["due_at"] is None


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        (
            "create_task",
            {
                "title": "无时区任务",
                "due_at": "2026-09-09T10:00:00",
            },
        ),
        (
            "update_task",
            {
                "task_id": 1,
                "due_at": "2026-09-09T10:00:00",
            },
        ),
    ],
)
def test_ai_write_tools_reject_naive_due_at(
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


def test_list_tasks_tool_declares_overdue_boolean() -> None:
    tool = next(item for item in TOOLS if item["function"]["name"] == "list_tasks")

    overdue_schema = tool["function"]["parameters"]["properties"]["overdue"]

    assert overdue_schema["type"] == "boolean"
    assert "逾期" in overdue_schema["description"]

    create_tool = next(
        item for item in TOOLS if item["function"]["name"] == "create_task"
    )

    assert "overdue" not in create_tool["function"]["parameters"]["properties"]


def test_list_tasks_tool_declares_upcoming_and_due_at_sort() -> None:
    list_tool = next(item for item in TOOLS if item["function"]["name"] == "list_tasks")
    properties = list_tool["function"]["parameters"]["properties"]

    due_within_days_schema = properties["due_within_days"]
    sort_schema = properties["sort"]

    assert due_within_days_schema["type"] == "integer"
    assert due_within_days_schema["minimum"] == 1
    assert due_within_days_schema["maximum"] == 365
    assert sort_schema["type"] == "string"
    assert sort_schema["enum"] == ["due_at"]

    create_tool = next(
        item for item in TOOLS if item["function"]["name"] == "create_task"
    )
    create_properties = create_tool["function"]["parameters"]["properties"]

    assert "due_within_days" not in create_properties
    assert "sort" not in create_properties


def test_ai_tool_list_tasks_filters_upcoming_and_sorts_due_at(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    now = datetime.now(UTC)

    no_due_at_task = Task(
        title="没有截止时间",
        description=None,
        status="pending",
        priority="medium",
        due_at=None,
        owner_id=user.id,
    )
    later_task = Task(
        title="三天后到期",
        description=None,
        status="pending",
        priority="medium",
        due_at=now + timedelta(days=3),
        owner_id=user.id,
    )
    earlier_task = Task(
        title="一天后到期",
        description=None,
        status="pending",
        priority="medium",
        due_at=now + timedelta(days=1),
        owner_id=user.id,
    )
    outside_window_task = Task(
        title="八天后到期",
        description=None,
        status="pending",
        priority="medium",
        due_at=now + timedelta(days=8),
        owner_id=user.id,
    )
    completed_task = Task(
        title="范围内但已经完成",
        description=None,
        status="done",
        priority="medium",
        due_at=now + timedelta(days=2),
        owner_id=user.id,
    )
    other_user_task = Task(
        title="其他用户即将到期",
        description=None,
        status="pending",
        priority="medium",
        due_at=now + timedelta(hours=1),
        owner_id=other_user.id,
    )

    db_session.add_all(
        [
            no_due_at_task,
            later_task,
            earlier_task,
            outside_window_task,
            completed_task,
            other_user_task,
        ]
    )
    db_session.commit()

    raw_result = execute_tool(
        name="list_tasks",
        arguments={
            "due_within_days": 7,
            "sort": "due_at",
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True
    assert result["count"] == 2
    assert [task["id"] for task in result["tasks"]] == [
        earlier_task.id,
        later_task.id,
    ]


def test_ai_tool_list_tasks_filters_overdue(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    overdue_task = Task(
        title="当前用户逾期任务",
        description=None,
        status="pending",
        priority="medium",
        due_at=datetime(
            2000,
            1,
            1,
            tzinfo=UTC,
        ),
        owner_id=user.id,
    )

    future_task = Task(
        title="当前用户未来任务",
        description=None,
        status="pending",
        priority="medium",
        due_at=datetime(
            2100,
            1,
            1,
            tzinfo=UTC,
        ),
        owner_id=user.id,
    )

    other_user_task = Task(
        title="其他用户逾期任务",
        description=None,
        status="pending",
        priority="medium",
        due_at=datetime(
            2000,
            1,
            1,
            tzinfo=UTC,
        ),
        owner_id=other_user.id,
    )

    db_session.add_all(
        [
            overdue_task,
            future_task,
            other_user_task,
        ]
    )
    db_session.commit()

    raw_result = execute_tool(
        name="list_tasks",
        arguments={
            "overdue": True,
        },
        db=db_session,
        owner_id=user.id,
    )

    result = json.loads(raw_result)

    assert result["success"] is True
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == overdue_task.id


@pytest.mark.parametrize(
    "arguments",
    [
        {
            "due_within_days": 0,
        },
        {
            "due_within_days": 366,
        },
        {
            "sort": "title",
        },
    ],
)
def test_ai_tool_list_tasks_rejects_invalid_upcoming_arguments(
    db_session: Session,
    user: User,
    arguments: dict[str, object],
) -> None:
    with pytest.raises(
        AIToolError,
        match="工具参数验证失败",
    ):
        execute_tool(
            name="list_tasks",
            arguments=arguments,
            db=db_session,
            owner_id=user.id,
        )
