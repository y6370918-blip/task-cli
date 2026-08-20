from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import task_cli.routers.assistant as assistant_router
from task_cli.action_service import create_pending_action
from task_cli.ai_exceptions import AIProviderError
from task_cli.models import Task, User


def test_assistant_returns_service_reply(
    authenticated_client: TestClient,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_task_assistant(
        db: Session,
        owner_id: int,
        message: str,
    ) -> str:
        assert owner_id == user.id
        assert message == "总结我的任务"
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
    assert response.json() == {
        "reply": "你目前没有任务。"
    }


def test_assistant_provider_error_returns_503(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_run_task_assistant(
        db: Session,
        owner_id: int,
        message: str,
    ) -> str:
        raise AIProviderError(
            "模拟 DeepSeek 不可用"
        )

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
    assert response.json() == {
        "detail": "AI 服务暂时不可用"
    }


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

    response = authenticated_client.post(
        f"/assistant/actions/{action.id}/confirm"
    )

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

    response = authenticated_client.post(
        f"/assistant/actions/{action.id}/cancel"
    )

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

    response = authenticated_client.post(
        f"/assistant/actions/{action.id}/confirm"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "待确认操作不存在"
    }


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
    action.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(minutes=1)
    )
    db_session.commit()

    response = authenticated_client.post(
        f"/assistant/actions/{action.id}/confirm"
    )

    assert response.status_code == 410
    assert response.json() == {
        "detail": "待确认操作已经过期"
    }


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
    action.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(minutes=1)
    )
    db_session.commit()

    response = authenticated_client.post(
        f"/assistant/actions/{action.id}/cancel"
    )

    assert response.status_code == 410
    assert response.json() == {
        "detail": "待确认操作已经过期"
    }
