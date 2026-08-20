from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user

from task_cli.models import Task
from task_cli.schemas import (
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)
from task_cli.exceptions import TaskNotFoundError

def create_task(
    session: Session,
    data: TaskCreate,
    owner_id: int,
) -> Task:

    task = Task(
        title=data.title,
        description=data.description,
        status="pending",
        owner_id=owner_id,
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    return task


def get_task(
    session: Session,
    task_id: int,
    owner_id: int,
) -> Task:

    statement = select(Task).where(
        Task.id == task_id,
        Task.owner_id == owner_id,
    )

    task = session.scalar(
        statement
    )

    if task is None:
        raise TaskNotFoundError(
            task_id
        )

    return task

def list_tasks(
    session: Session,
    owner_id: int,
    status: TaskStatus | None = None,
) -> list[Task]:

    statement = select(Task).where(
        Task.owner_id==owner_id
    )

    if status:
        statement = statement.where(Task.status == status)

    result = session.scalars(statement)

    return list(result)


def update_task(
    session: Session,
    task_id: int,
    data: TaskUpdate,
    owner_id: int,
) -> Task:

    statement = select(Task).where(
        Task.id == task_id,
        Task.owner_id == owner_id,
    )

    task = session.scalar(statement)

    if task is None:
        raise TaskNotFoundError(task_id)

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(
            task,
            field,
            value,
        )

    session.commit()
    session.refresh(task)

    return task


def delete_task(
    session: Session,
    task_id: int,
    owner_id: int,
) -> bool:

    statement = select(Task).where(
        Task.id == task_id,
        Task.owner_id == owner_id,
    )

    task = session.scalar(
        statement
    )

    if task is None:
        return False

    session.delete(task)
    session.commit()

    return True
