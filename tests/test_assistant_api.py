from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import task_cli.routers.assistant as assistant_router
from task_cli.action_service import create_pending_action
from task_cli.ai_exceptions import AIProviderError
from task_cli.conversation_service import (
    create_conversation,
    create_message,
)
from task_cli.models import Conversation, Task, User


def test_assistant_creates_conversation_and_returns_reply(
    authenticated_client: TestClient,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_task_assistant(
        db: Session,
        owner_id: int,
        message: str,
        conversation_id: int,
    ) -> str:
        assert owner_id == user.id
        assert message == "总结我的任务"

        conversation = db.get(
            Conversation,
            conversation_id,
        )

        assert conversation is not None
        assert conversation.owner_id == user.id

        return "你目前没有任务。"

    monkeypatch.setattr(
        assistant_router,
        "run_task_assistant",
        fake_run_task_assistant,
    )

    response = authenticated_client.post(
        "/assistant/",
        json={
            "message": "总结我的任务",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["reply"] == "你目前没有任务。"
    assert isinstance(
        data["conversation_id"],
        int,
    )
    assert data["conversation_id"] > 0


def test_assistant_continues_owned_conversation(
    authenticated_client: TestClient,
    db_session: Session,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    def fake_run_task_assistant(
        db: Session,
        owner_id: int,
        message: str,
        conversation_id: int,
    ) -> str:
        assert db is db_session
        assert owner_id == user.id
        assert message == "继续刚才的内容"
        assert conversation_id == conversation.id

        return "已经继续该会话。"

    monkeypatch.setattr(
        assistant_router,
        "run_task_assistant",
        fake_run_task_assistant,
    )

    response = authenticated_client.post(
        "/assistant/",
        json={
            "message": "继续刚才的内容",
            "conversation_id": conversation.id,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": conversation.id,
        "reply": "已经继续该会话。",
    }


def test_assistant_provider_error_returns_503(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_run_task_assistant(
        db: Session,
        owner_id: int,
        message: str,
        conversation_id: int,
    ) -> str:
        raise AIProviderError("模拟 DeepSeek 不可用")

    monkeypatch.setattr(
        assistant_router,
        "run_task_assistant",
        failing_run_task_assistant,
    )

    response = authenticated_client.post(
        "/assistant/",
        json={
            "message": "查询我的任务",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "AI 服务暂时不可用"}


def test_confirm_action_deletes_task(
    authenticated_client: TestClient,
    db_session: Session,
    user: User,
    task: Task,
) -> None:
    task_id = task.id
    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task_id,
        },
    )

    response = authenticated_client.post(f"/assistant/actions/{action.id}/confirm")

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert db_session.get(Task, task_id) is None


def test_cancel_action_keeps_task(
    authenticated_client: TestClient,
    db_session: Session,
    user: User,
    task: Task,
) -> None:
    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task.id,
        },
    )

    response = authenticated_client.post(f"/assistant/actions/{action.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert db_session.get(Task, task.id) is not None


def test_other_user_cannot_confirm_action(
    authenticated_client: TestClient,
    db_session: Session,
    other_user: User,
) -> None:
    action = create_pending_action(
        session=db_session,
        owner_id=other_user.id,
        action="delete_task",
        payload={
            "task_id": 1,
        },
    )

    response = authenticated_client.post(f"/assistant/actions/{action.id}/confirm")

    assert response.status_code == 404
    assert response.json() == {"detail": "待确认操作不存在"}


def test_confirm_expired_action_returns_410(
    authenticated_client: TestClient,
    db_session: Session,
    user: User,
) -> None:
    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": 1,
        },
    )
    action.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    response = authenticated_client.post(f"/assistant/actions/{action.id}/confirm")

    assert response.status_code == 410
    assert response.json() == {"detail": "待确认操作已经过期"}


def test_cancel_expired_action_returns_410(
    authenticated_client: TestClient,
    db_session: Session,
    user: User,
) -> None:
    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": 1,
        },
    )
    action.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    response = authenticated_client.post(f"/assistant/actions/{action.id}/cancel")

    assert response.status_code == 410
    assert response.json() == {"detail": "待确认操作已经过期"}


def test_assistant_hides_other_users_conversation(
    authenticated_client: TestClient,
    db_session: Session,
    other_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=other_user.id,
    )

    provider_was_called = False

    def fake_run_task_assistant(
        db: Session,
        owner_id: int,
        message: str,
        conversation_id: int,
    ) -> str:
        nonlocal provider_was_called
        provider_was_called = True

        return "不应该执行到这里"

    monkeypatch.setattr(
        assistant_router,
        "run_task_assistant",
        fake_run_task_assistant,
    )

    response = authenticated_client.post(
        "/assistant/",
        json={
            "message": "读取其他用户的会话",
            "conversation_id": conversation.id,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "会话不存在",
    }
    assert provider_was_called is False


def test_list_conversations_returns_current_users_only(
    authenticated_client: TestClient,
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    first_conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    create_conversation(
        session=db_session,
        owner_id=other_user.id,
    )

    latest_conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    response = authenticated_client.get("/assistant/conversations")

    assert response.status_code == 200
    assert [conversation["id"] for conversation in response.json()] == [
        latest_conversation.id,
        first_conversation.id,
    ]


def test_conversation_messages_hide_tool_protocol(
    authenticated_client: TestClient,
    db_session: Session,
    user: User,
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
        content="查询我的任务",
    )

    create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="assistant",
        content=None,
        tool_calls=[
            {
                "id": "call-list-1",
                "type": "function",
            }
        ],
    )

    create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="tool",
        content='{"success": true}',
        tool_call_id="call-list-1",
    )

    create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="assistant",
        content="你目前没有任务。",
    )

    response = authenticated_client.get(
        f"/assistant/conversations/{conversation.id}/messages"
    )

    assert response.status_code == 200

    messages = response.json()

    assert [
        (
            message["role"],
            message["content"],
        )
        for message in messages
    ] == [
        (
            "user",
            "查询我的任务",
        ),
        (
            "assistant",
            "你目前没有任务。",
        ),
    ]

    assert all(
        set(message)
        == {
            "id",
            "role",
            "content",
            "created_at",
        }
        for message in messages
    )


def test_other_user_cannot_read_conversation_messages(
    authenticated_client: TestClient,
    db_session: Session,
    other_user: User,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=other_user.id,
    )

    response = authenticated_client.get(
        f"/assistant/conversations/{conversation.id}/messages"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "会话不存在",
    }
