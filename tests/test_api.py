from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from task_cli.models import Task, User


def test_create_task(
    authenticated_client,
):

    response = authenticated_client.post(
        "/tasks/", json={"title": "测试任务", "description": "API测试"}
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "测试任务"


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
