import json
import logging
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import task_cli.ai_service as ai_service
from task_cli.ai_exceptions import (
    AIProviderConnectionError,
    AIProviderError,
    AIToolError,
)
from task_cli.conversation_service import (
    create_conversation,
    create_message,
    list_conversation_messages,
)
from task_cli.models import Message, Task, User


def make_text_response(content: str) -> SimpleNamespace:
    """构造一条不包含 Tool Call 的模型回复。"""

    message = SimpleNamespace(
        content=content,
        tool_calls=None,
    )

    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


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

    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


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
            make_text_response("你有一个进行中的任务：学习 Mock。"),
        ]
    )

    provider_messages: list[list[dict]] = []

    def fake_provider(messages: list[dict]):
        provider_messages.append(deepcopy(messages))
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

    assert reply == ("你有一个进行中的任务：学习 Mock。")
    assert len(provider_messages) == 2

    tool_message = provider_messages[1][-1]
    tool_result = json.loads(tool_message["content"])

    assert tool_message["role"] == "tool"
    assert tool_result["success"] is True
    assert tool_result["tasks"][0]["title"] == ("学习 Mock")


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
                "priority": "high",
                "due_at": "2026-09-10T18:00:00+08:00",
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

    tasks = list(db_session.scalars(select(Task).where(Task.owner_id == user.id)))

    assert provider_call_count == 1
    assert len(tasks) == 1
    assert tasks[0].title == "完成 Day24"
    assert tasks[0].priority == "high"
    assert tasks[0].due_at is not None
    assert reply == (
        f"任务已创建：#{tasks[0].id} "
        f"完成 Day24，"
        f"当前状态为 pending，"
        f"优先级为 high。"
        f"截止时间为 "
        f"{tasks[0].due_at.isoformat()}。"
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
            make_text_response("已经使用第一次查询结果回答。"),
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
        raise AIProviderError("模拟 DeepSeek 不可用")

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


def test_update_task_priority_returns_immediately(
    db_session: Session,
    user: User,
    task: Task,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_call_count = 0

    def fake_provider(
        messages: list[dict],
    ):
        nonlocal provider_call_count
        provider_call_count += 1

        return make_tool_response(
            call_id="call-update-priority-1",
            name="update_task",
            arguments={
                "task_id": task.id,
                "priority": "high",
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
        message="把这个任务改成高优先级",
    )

    db_session.refresh(task)

    assert provider_call_count == 1
    assert task.priority == "high"
    assert reply == (
        f"任务 #{task.id} "
        f"已修改成功。"
        f"当前状态为 pending，"
        f"优先级为 high。"
        f"截止时间为 未设置。"
    )


def test_clear_task_due_at_returns_immediately(
    db_session: Session,
    user: User,
    task: Task,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task.due_at = datetime(
        2026,
        9,
        11,
        10,
        0,
        tzinfo=UTC,
    )

    db_session.commit()

    provider_call_count = 0

    def fake_provider(
        messages: list[dict],
    ):
        nonlocal provider_call_count
        provider_call_count += 1

        return make_tool_response(
            call_id="call-clear-due-at-1",
            name="update_task",
            arguments={
                "task_id": task.id,
                "due_at": None,
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
        message="清除这个任务的截止时间",
    )

    db_session.refresh(task)

    assert provider_call_count == 1
    assert task.due_at is None
    assert reply == (
        f"任务 #{task.id} "
        f"已修改成功。"
        f"当前状态为 {task.status}，"
        f"优先级为 {task.priority}。"
        f"截止时间为 未设置。"
    )


def test_system_prompt_requires_explicit_deadline_context() -> None:
    assert "相对或模糊时间" in ai_service.SYSTEM_PROMPT
    assert "明确日期和时区" in ai_service.SYSTEM_PROMPT


def test_agent_logs_round_and_tool_without_sensitive_content(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_user_message = "这是不能写入日志的私人任务"
    sensitive_tool_argument = "这是不能写入日志的任务标题"

    def fake_provider(
        messages: list[dict],
    ) -> SimpleNamespace:
        return make_tool_response(
            call_id="call-private-create",
            name="create_task",
            arguments={
                "title": sensitive_tool_argument,
            },
        )

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )

    with caplog.at_level(
        logging.INFO,
        logger="task_cli.ai_service",
    ):
        reply = ai_service.run_task_assistant(
            db=db_session,
            owner_id=user.id,
            message=sensitive_user_message,
        )

    service_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "task_cli.ai_service"
    ]

    assert f"AI agent round=1 owner_id={user.id}" in service_messages
    assert f"AI tool call name=create_task owner_id={user.id}" in service_messages

    logged_text = "\n".join(service_messages)

    assert sensitive_user_message not in logged_text
    assert sensitive_tool_argument not in logged_text
    assert sensitive_tool_argument in reply


def test_provider_failure_log_does_not_expose_exception_chain(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_provider_detail = "sensitive-provider-response-body"

    def failing_provider(
        messages: list[dict],
    ) -> None:
        try:
            raise RuntimeError(sensitive_provider_detail)
        except RuntimeError as exc:
            raise AIProviderConnectionError("无法连接 DeepSeek API") from exc

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        failing_provider,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="task_cli.ai_service",
    ):
        with pytest.raises(
            AIProviderConnectionError,
        ):
            ai_service.run_task_assistant(
                db=db_session,
                owner_id=user.id,
                message="查询任务",
            )

    service_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "task_cli.ai_service"
    ]

    assert (
        f"AI provider failed "
        f"owner_id={user.id} "
        f"error_type=AIProviderConnectionError" in service_messages
    )
    assert sensitive_provider_detail not in caplog.text


def test_assistant_loads_and_persists_conversation_history(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="user",
        content="我之前问过什么？",
    )

    create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="assistant",
        content="你之前询问了任务情况。",
    )

    provider_messages: list[list[dict]] = []

    def fake_provider(
        messages: list[dict],
    ) -> SimpleNamespace:
        provider_messages.append(deepcopy(messages))

        return make_text_response("现在继续处理你的任务。")

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )

    reply = ai_service.run_task_assistant(
        db=db_session,
        owner_id=user.id,
        message="那我们继续吧",
        conversation_id=conversation.id,
    )

    assert reply == "现在继续处理你的任务。"

    assert [
        (
            message["role"],
            message["content"],
        )
        for message in provider_messages[0]
    ] == [
        (
            "system",
            ai_service.SYSTEM_PROMPT,
        ),
        (
            "user",
            "我之前问过什么？",
        ),
        (
            "assistant",
            "你之前询问了任务情况。",
        ),
        (
            "user",
            "那我们继续吧",
        ),
    ]

    persisted_messages = list_conversation_messages(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
    )

    assert [
        (
            message.role,
            message.content,
        )
        for message in persisted_messages
    ] == [
        (
            "user",
            "我之前问过什么？",
        ),
        (
            "assistant",
            "你之前询问了任务情况。",
        ),
        (
            "user",
            "那我们继续吧",
        ),
        (
            "assistant",
            "现在继续处理你的任务。",
        ),
    ]


def test_assistant_persists_tool_call_protocol(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    responses = iter(
        [
            make_tool_response(
                call_id="call-history-list-1",
                name="list_tasks",
                arguments={},
            ),
            make_text_response("你目前没有任务。"),
        ]
    )

    def fake_provider(
        messages: list[dict],
    ) -> SimpleNamespace:
        return next(responses)

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )

    reply = ai_service.run_task_assistant(
        db=db_session,
        owner_id=user.id,
        message="查询我的任务",
        conversation_id=conversation.id,
    )

    assert reply == "你目前没有任务。"

    history = list_conversation_messages(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
    )

    assert [message.role for message in history] == [
        "user",
        "assistant",
        "tool",
        "assistant",
    ]

    assert history[1].content is None
    assert history[1].tool_calls is not None
    assert history[1].tool_calls[0]["id"] == "call-history-list-1"

    assert history[2].tool_call_id == "call-history-list-1"
    assert history[3].content == "你目前没有任务。"


def test_provider_failure_keeps_user_message(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    def failing_provider(
        messages: list[dict],
    ) -> None:
        raise AIProviderError("模拟 Provider 失败")

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        failing_provider,
    )

    with pytest.raises(
        AIProviderError,
    ):
        ai_service.run_task_assistant(
            db=db_session,
            owner_id=user.id,
            message="这条消息必须保留",
            conversation_id=conversation.id,
        )

    history = list_conversation_messages(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
    )

    assert [
        (
            message.role,
            message.content,
        )
        for message in history
    ] == [
        (
            "user",
            "这条消息必须保留",
        ),
    ]


def test_write_tool_generated_reply_is_persisted(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    def fake_provider(
        messages: list[dict],
    ) -> SimpleNamespace:
        return make_tool_response(
            call_id="call-persist-create-1",
            name="create_task",
            arguments={
                "title": "保存写操作回复",
                "priority": "high",
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
        message="创建一个高优先级任务",
        conversation_id=conversation.id,
    )

    history = list_conversation_messages(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
    )

    assert [message.role for message in history] == [
        "user",
        "assistant",
        "tool",
        "assistant",
    ]

    assert history[-1].content == reply
    assert "保存写操作回复" in reply


def test_assistant_uses_safe_history_selector(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    older_message = create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="user",
        content="较早的历史",
    )

    recent_message = create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="assistant",
        content="选择器保留的历史",
    )

    candidates = [
        older_message,
        recent_message,
    ]

    def fake_list_conversation_messages(
        session: Session,
        conversation_id: int,
        owner_id: int,
        limit: int,
    ) -> list[Message]:
        assert session is db_session
        assert conversation_id == conversation.id
        assert owner_id == user.id
        assert limit == ai_service.HISTORY_CANDIDATE_LIMIT

        return candidates

    def fake_select_history_messages(
        messages: list[Message],
    ) -> list[Message]:
        assert messages == candidates

        return [
            recent_message,
        ]

    provider_messages: list[list[dict]] = []

    def fake_provider(
        messages: list[dict],
    ) -> SimpleNamespace:
        provider_messages.append(deepcopy(messages))

        return make_text_response("已经使用安全历史回答。")

    monkeypatch.setattr(
        ai_service,
        "list_conversation_messages",
        fake_list_conversation_messages,
    )
    monkeypatch.setattr(
        ai_service,
        "select_history_messages",
        fake_select_history_messages,
        raising=False,
    )
    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )

    reply = ai_service.run_task_assistant(
        db=db_session,
        owner_id=user.id,
        message="这是当前消息",
        conversation_id=conversation.id,
    )

    assert reply == ("已经使用安全历史回答。")

    assert [
        (
            message["role"],
            message["content"],
        )
        for message in provider_messages[0]
    ] == [
        (
            "system",
            ai_service.SYSTEM_PROMPT,
        ),
        (
            "assistant",
            "选择器保留的历史",
        ),
        (
            "user",
            "这是当前消息",
        ),
    ]


def test_tool_failure_log_does_not_expose_error_detail(
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_error_detail = "不能写入日志的私人任务标题"

    responses = iter(
        [
            make_tool_response(
                call_id="call-sensitive-error-1",
                name="list_tasks",
                arguments={},
            ),
            make_text_response("工具调用失败，请检查任务条件。"),
        ]
    )

    def fake_provider(
        messages: list[dict],
    ) -> SimpleNamespace:
        return next(responses)

    def failing_execute_tool(
        **kwargs: object,
    ) -> str:
        raise AIToolError(f"工具参数验证失败：{sensitive_error_detail}")

    monkeypatch.setattr(
        ai_service,
        "call_ai_provider",
        fake_provider,
    )
    monkeypatch.setattr(
        ai_service,
        "execute_tool",
        failing_execute_tool,
    )

    with caplog.at_level(
        logging.WARNING,
        logger="task_cli.ai_service",
    ):
        ai_service.run_task_assistant(
            db=db_session,
            owner_id=user.id,
            message="查询我的私人任务",
        )

    service_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "task_cli.ai_service"
    ]

    assert sensitive_error_detail not in caplog.text
    assert (
        f"AI tool failed "
        f"name=list_tasks "
        f"owner_id={user.id} "
        f"error_type=AIToolError" in service_messages
    )
