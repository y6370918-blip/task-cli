import pytest
from pydantic import ValidationError
from task_cli.schemas import TaskCreate, TaskUpdate, TaskRead


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
