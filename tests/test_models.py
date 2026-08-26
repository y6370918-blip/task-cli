import pytest
from pydantic import ValidationError

from task_cli.schemas import TaskCreate, TaskUpdate


def test_create_task_success():
    task = TaskCreate(title="学习pydantic")
    assert task.title == "学习pydantic"


def test_title_cannot_be_empty():
    with pytest.raises(ValidationError):
        TaskCreate(title="")


def test_title_lenth_limit():
    with pytest.raises(ValidationError):
        TaskCreate(title="A" * 101)


def test_description_can_be_none():
    task = TaskCreate(title="测试")

    assert task.description is None


def test_status_vaildation():
    task = TaskUpdate(status="done")

    assert task.status == "done"


def test_task_priority_defaults_to_medium() -> None:
    task = TaskCreate(
        title="默认优先级任务",
    )

    assert task.priority == "medium"


@pytest.mark.parametrize(
    "priority",
    [
        "low",
        "medium",
        "high",
    ],
)
def test_task_priority_accepts_allowed_values(
    priority: str,
) -> None:
    task = TaskCreate(
        title="合法优先级任务",
        priority=priority,
    )

    assert task.priority == priority


def test_task_priority_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(
            title="非法优先级任务",
            priority="urgent",
        )


def test_task_update_rejects_null_priority() -> None:
    with pytest.raises(
        ValidationError,
        match="priority cannot be null",
    ):
        TaskUpdate(
            priority=None,
        )
