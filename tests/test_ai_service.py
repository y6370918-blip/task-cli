import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import task_cli.ai_service as ai_service
from task_cli.ai_exceptions import AIProviderError
from task_cli.models import Task, User


def make_text_response(content: str) -> SimpleNamespace:
    """构造一条不包含 Tool Call 的模型回复。"""

    message = SimpleNamespace(
        content=content,
        tool_calls=None,
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=message)
        ]
    )


def make_tool_response(
    call_id: str,
    name: str,
    arguments: dict,
) -> SimpleNamespace:
    """构造一条要求调用 Python Tool 的模型回复。"""

    tool_call = SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(
                arguments,
                ensure_ascii=False,
            ),
        ),
    )

    message = SimpleNamespace(
        content=None,
        tool_calls=[tool_call],
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=message)
        ]
    )


def test_list_tasks_uses_tool_result_in_second_round(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = Task(
        title="学习 Mock",
        description="验证 AI 多轮调用",
        status="doing",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()

    responses = iter(
        [
            make_tool_response(
                call_id="call-list-1",
                name="list_tasks",
                arguments={},
            ),
            make_text_response(
                "你有一个进行中的任务：学习 Mock。"
            ),
        ]
    )

    provider_messages: list[list[dict]] = []

    def fake_provider(messages: list[dict]):
        provider_messages.append(
            deepcopy(messages)
        )
        return next(responses)

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )

    reply = ai_service.run_task_assistant(
        db=db_session,
        owner_id=user.id,
        message="我现在有哪些任务？",
    )

    assert reply == (
        "你有一个进行中的任务：学习 Mock。"
    )
    assert len(provider_messages) == 2

    tool_message = provider_messages[1][-1]
    tool_result = json.loads(
        tool_message["content"]
    )

    assert tool_message["role"] == "tool"
    assert tool_result["success"] is True
    assert tool_result["tasks"][0]["title"] == (
        "学习 Mock"
    )


def test_create_task_executes_once_and_returns_immediately(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_call_count = 0

    def fake_provider(messages: list[dict]):
        nonlocal provider_call_count
        provider_call_count += 1

        return make_tool_response(
            call_id="call-create-1",
            name="create_task",
            arguments={
                "title": "完成 Day24",
                "description": "验证写操作只执行一次",
            },
        )

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )

    reply = ai_service.run_task_assistant(
        db=db_session,
        owner_id=user.id,
        message="帮我创建完成 Day24 的任务",
    )

    tasks = list(
        db_session.scalars(
            select(Task).where(
                Task.owner_id == user.id
            )
        )
    )

    assert provider_call_count == 1
    assert len(tasks) == 1
    assert tasks[0].title == "完成 Day24"
    assert reply == (
        f"任务已创建：#{tasks[0].id} "
        "完成 Day24，当前状态为 pending。"
    )


def test_duplicate_tool_call_is_not_executed_twice(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            make_tool_response(
                call_id="call-list-1",
                name="list_tasks",
                arguments={},
            ),
            make_tool_response(
                call_id="call-list-2",
                name="list_tasks",
                arguments={},
            ),
            make_text_response(
                "已经使用第一次查询结果回答。"
            ),
        ]
    )

    def fake_provider(messages: list[dict]):
        return next(responses)

    real_execute_tool = ai_service.execute_tool
    execute_count = 0

    def counting_execute_tool(**kwargs):
        nonlocal execute_count
        execute_count += 1
        return real_execute_tool(**kwargs)

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )
    monkeypatch.setattr(
        ai_service,
        "execute_tool",
        counting_execute_tool,
    )

    reply = ai_service.run_task_assistant(
        db=db_session,
        owner_id=user.id,
        message="查询我的任务",
    )

    assert execute_count == 1
    assert reply == "已经使用第一次查询结果回答。"


def test_provider_error_is_propagated(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_provider(messages: list[dict]):
        raise AIProviderError(
            "模拟 DeepSeek 不可用"
        )

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        failing_provider,
    )

    with pytest.raises(
        AIProviderError,
        match="模拟 DeepSeek 不可用",
    ):
        ai_service.run_task_assistant(
            db=db_session,
            owner_id=user.id,
            message="查询我的任务",
        )
