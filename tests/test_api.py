from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from task_cli.models import Task, User


def _as_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def test_create_task(
    authenticated_client,
):
    response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "测试任务",
            "description": "API测试",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "测试任务"
    assert data["priority"] == "medium"


def test_list_tasks(authenticated_client):

    authenticated_client.post("/tasks/", json={"title": "任务1"})

    response = authenticated_client.get("/tasks/")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1


def test_get_missing_task(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": "TASK_NOT_FOUND",
        "message": "Task 999 not found",
    }


def test_update_task(authenticated_client):

    create = authenticated_client.post("/tasks/", json={"title": "旧标题"})

    task_id = create.json()["id"]

    response = authenticated_client.put(f"/tasks/{task_id}", json={"status": "done"})

    assert response.status_code == 200

    assert response.json()["status"] == "done"


def test_delete_task(authenticated_client):

    create = authenticated_client.post("/tasks/", json={"title": "删除测试"})

    task_id = create.json()["id"]

    response = authenticated_client.delete(f"/tasks/{task_id}")

    assert response.status_code == 200


def test_update_missing_task_uses_global_handler(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.put(
        "/tasks/999",
        json={
            "status": "done",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "TASK_NOT_FOUND",
        "message": "Task 999 not found",
    }


def test_delete_missing_task_uses_global_handler(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.delete("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": "TASK_NOT_FOUND",
        "message": "Task 999 not found",
    }


def test_other_users_task_looks_missing(
    authenticated_client: TestClient,
    db_session: Session,
    other_user: User,
) -> None:
    other_task = Task(
        title="其他用户的任务",
        description=None,
        status="pending",
        owner_id=other_user.id,
    )

    db_session.add(other_task)
    db_session.commit()
    db_session.refresh(other_task)

    get_response = authenticated_client.get(f"/tasks/{other_task.id}")
    update_response = authenticated_client.put(
        f"/tasks/{other_task.id}",
        json={
            "status": "done",
        },
    )
    delete_response = authenticated_client.delete(f"/tasks/{other_task.id}")

    expected_response = {
        "error": "TASK_NOT_FOUND",
        "message": (f"Task {other_task.id} not found"),
    }

    for response in (
        get_response,
        update_response,
        delete_response,
    ):
        assert response.status_code == 404
        assert response.json() == expected_response

    assert (
        db_session.get(
            Task,
            other_task.id,
        )
        is not None
    )


def test_list_tasks_filters_by_status_query(
    authenticated_client: TestClient,
) -> None:
    pending_response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "待处理任务",
        },
    )
    done_response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "已完成任务",
        },
    )

    done_task_id = done_response.json()["id"]

    authenticated_client.put(
        f"/tasks/{done_task_id}",
        json={
            "status": "done",
        },
    )

    response = authenticated_client.get(
        "/tasks/",
        params={
            "status": "done",
        },
    )

    assert pending_response.status_code == 201
    assert done_response.status_code == 201
    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [done_task_id]


def test_list_tasks_applies_query_pagination(
    authenticated_client: TestClient,
) -> None:
    created_tasks = [
        authenticated_client.post(
            "/tasks/",
            json={
                "title": f"任务 {number}",
            },
        ).json()
        for number in range(1, 6)
    ]

    response = authenticated_client.get(
        "/tasks/",
        params={
            "limit": 2,
            "offset": 2,
        },
    )

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        created_tasks[2]["id"],
        created_tasks[3]["id"],
    ]


@pytest.mark.parametrize(
    "params",
    [
        {
            "status": "finished",
        },
        {
            "priority": "urgent",
        },
        {
            "limit": 0,
        },
        {
            "limit": 101,
        },
        {
            "offset": -1,
        },
    ],
)
def test_list_tasks_rejects_invalid_query(
    authenticated_client: TestClient,
    params: dict[str, str | int],
) -> None:
    response = authenticated_client.get(
        "/tasks/",
        params=params,
    )

    assert response.status_code == 422


def test_create_task_with_priority(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "紧急任务",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    assert response.json()["priority"] == "high"


def test_update_task_priority(
    authenticated_client: TestClient,
) -> None:
    create_response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "调整优先级",
        },
    )

    task_id = create_response.json()["id"]

    response = authenticated_client.put(
        f"/tasks/{task_id}",
        json={
            "priority": "high",
        },
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "high"


def test_create_task_rejects_invalid_priority(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "非法优先级",
            "priority": "urgent",
        },
    )

    assert response.status_code == 422


def test_update_task_rejects_null_priority(
    authenticated_client: TestClient,
) -> None:
    create_response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "不能清空优先级",
        },
    )

    task_id = create_response.json()["id"]

    response = authenticated_client.put(
        f"/tasks/{task_id}",
        json={
            "priority": None,
        },
    )

    assert response.status_code == 422


def test_list_tasks_filters_by_priority_query(
    authenticated_client: TestClient,
) -> None:
    high_response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "高优先级任务",
            "priority": "high",
        },
    )

    authenticated_client.post(
        "/tasks/",
        json={
            "title": "普通任务",
            "priority": "medium",
        },
    )

    response = authenticated_client.get(
        "/tasks/",
        params={
            "priority": "high",
        },
    )

    assert high_response.status_code == 201
    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [
        high_response.json()["id"],
    ]


def test_create_task_with_due_at(
    authenticated_client: TestClient,
) -> None:
    due_at = datetime(
        2026,
        9,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "按时完成 Day36",
            "due_at": due_at.isoformat(),
        },
    )

    assert response.status_code == 201
    assert _as_utc(response.json()["due_at"]) == due_at


def test_update_task_due_at(
    authenticated_client: TestClient,
) -> None:
    create_response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "设置截止时间",
        },
    )

    task_id = create_response.json()["id"]

    due_at = datetime(
        2026,
        9,
        2,
        18,
        0,
        tzinfo=UTC,
    )

    response = authenticated_client.put(
        f"/tasks/{task_id}",
        json={
            "due_at": due_at.isoformat(),
        },
    )

    assert response.status_code == 200
    assert _as_utc(response.json()["due_at"]) == due_at


def test_clear_task_due_at(
    authenticated_client: TestClient,
) -> None:
    create_response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "清除截止时间",
            "due_at": "2026-09-03T10:00:00+00:00",
        },
    )

    task_id = create_response.json()["id"]

    response = authenticated_client.put(
        f"/tasks/{task_id}",
        json={
            "due_at": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["due_at"] is None


def test_create_task_rejects_naive_due_at(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/tasks/",
        json={
            "title": "没有时区的截止时间",
            "due_at": "2026-09-03T10:00:00",
        },
    )

    assert response.status_code == 422
