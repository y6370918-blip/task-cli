from sqlalchemy import select
from sqlalchemy.orm import Session
from task_cli.models import Task
from task_cli.schemas import (
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)


def create_task(
    session: Session,
    data: TaskCreate,
) -> Task:

    task = Task(
        title=data.title,
        description=data.description,
        status="pending",
    )

    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def get_task(
    session: Session,
    task_id: int,
) -> Task | None:

    return session.get(Task, task_id)


def list_tasks(
    session: Session,
    status: TaskStatus | None = None,
) -> list[Task]:

    statement = select(Task)
    if status:
        statement = statement.where(Task.status == status)

    result = session.scalars(statement)

    return list(result)


def updata_task(
    session: Session,
    task_id: int,
    data: TaskUpdate,
) -> Task | None:

    task = session.get(Task, task_id)

    if task is None:
        return None

    if data.title is not None:
        task.title = data.title

    if data.description is not None:
        task.description = data.description

    if data.status is not None:
        task.status = data.status

    session.commit()

    session.refresh(task)

    return task


def delete_task(
    session: Session,
    task_id: int,
) -> bool:

    task = session.get(Task, task_id)

    if task is None:
        return False

    session.delete(task)

    session.commit()

    return True
