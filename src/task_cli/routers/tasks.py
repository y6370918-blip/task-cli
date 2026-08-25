from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from task_cli.auth_dependencies import (
    get_current_user,
)
from task_cli.dependencies import get_db
from task_cli.models import User
from task_cli.schemas import (
    TaskCreate,
    TaskRead,
    TaskStatus,
    TaskUpdate,
)
from task_cli.services import (
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


# =========================================================
# 创建任务
# =========================================================


@router.post(
    "/",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task_api(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_task(
        db,
        data,
        current_user.id,
    )


# =========================================================
# 查询当前用户的所有任务
# =========================================================


@router.get(
    "/",
    response_model=list[TaskRead],
)
def list_tasks_api(
    task_status: Annotated[
        TaskStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_tasks(
        db,
        owner_id=current_user.id,
        status=task_status,
        limit=limit,
        offset=offset,
    )


# =========================================================
# 查询当前用户的某一个任务
# =========================================================


@router.get(
    "/{task_id}",
    response_model=TaskRead,
)
def get_task_api(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_task(
        db,
        task_id,
        current_user.id,
    )


# =========================================================
# 更新当前用户的任务
# =========================================================


@router.put(
    "/{task_id}",
    response_model=TaskRead,
)
def update_task_api(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_task(
        db,
        task_id,
        data,
        current_user.id,
    )


# =========================================================
# 删除当前用户的任务
# =========================================================


@router.delete(
    "/{task_id}",
)
def delete_task_api(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_task(
        db,
        task_id,
        current_user.id,
    )

    return {"message": "Task deleted"}
