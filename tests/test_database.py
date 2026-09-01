from sqlalchemy.orm import Session

from task_cli.models import Task, User


def test_create_task(
    db_session: Session,
    user: User,
):
    task = Task(
        title="Test Task",
        description="Test Description",
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.owner_id == user.id
