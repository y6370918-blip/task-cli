def test_create_task(
    authenticated_client,
    ):

    response = authenticated_client.post(
        "/tasks/",
        json={
            "title":"测试任务",
            "description":"API测试"
        }
    )


    assert response.status_code == 201


    data = response.json()


    assert data["title"] == "测试任务"

def test_list_tasks(authenticated_client):

    authenticated_client.post(
        "/tasks/",
        json={
            "title":"任务1"
        }
    )


    response = authenticated_client.get(
        "/tasks/"
    )


    assert response.status_code == 200


    data = response.json()


    assert len(data) == 1

def test_get_missing_task(authenticated_client):

    response = authenticated_client.get(
        "/tasks/999"
    )


    assert response.status_code == 404

def test_update_task(authenticated_client):

    create = authenticated_client.post(
        "/tasks/",
        json={
            "title":"旧标题"
        }
    )


    task_id = create.json()["id"]


    response = authenticated_client.put(
        f"/tasks/{task_id}",
        json={
            "status":"done"
        }
    )


    assert response.status_code == 200


    assert response.json()["status"]=="done"

def test_delete_task(authenticated_client):

    create = authenticated_client.post(
        "/tasks/",
        json={
            "title":"删除测试"
        }
    )


    task_id = create.json()["id"]


    response = authenticated_client.delete(
        f"/tasks/{task_id}"
    )


    assert response.status_code == 200