import pytest
from sqlalchemy.orm import Session

from task_cli.action_exceptions import (
    PendingActionAlreadyHandledError,
    PendingActionNotFoundError,
)
from task_cli.action_service import (
    cancel_pending_action,
    confirm_pending_action,
    create_pending_action,
)
from task_cli.models import Task, User


def test_create_pending_action(
    db_session: Session,
    user: User,
) -> None:

    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": 10,
        },
    )

    assert action.id is not None

    assert action.owner_id == user.id

    assert action.action == "delete_task"

    assert action.payload == {"task_id": 10}

    assert action.status == "pending"

    assert action.expires_at is not None


def test_confirm_delete_task(
    db_session: Session,
    user: User,
) -> None:

    task = Task(
        title="需要删除的任务",
        description=None,
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    task_id = task.id

    pending_action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task_id,
        },
    )

    result = confirm_pending_action(
        session=db_session,
        action_id=pending_action.id,
        owner_id=user.id,
    )

    assert result.status == "confirmed"

    deleted_task = db_session.get(
        Task,
        task_id,
    )
    assert deleted_task is None


def test_create_delete_request_does_not_delete_task(
    db_session: Session,
    user: User,
) -> None:

    task = Task(
        title="不能立即删除",
        description=None,
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    task_id = task.id

    create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task_id,
        },
    )

    existing_task = db_session.get(
        Task,
        task_id,
    )

    assert existing_task is not None


def test_cannot_confirm_twice(
    db_session: Session,
    user: User,
) -> None:

    task = Task(
        title="只能删除一次",
        description=None,
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task.id,
        },
    )

    confirm_pending_action(
        session=db_session,
        action_id=action.id,
        owner_id=user.id,
    )

    with pytest.raises(PendingActionAlreadyHandledError):
        confirm_pending_action(
            session=db_session,
            action_id=action.id,
            owner_id=user.id,
        )


def test_other_user_cannot_confirm_action(
    db_session: Session,
    user: User,
) -> None:

    other_user = User(
        username="jerry",
        email="jerry@example.com",
        password_hash="test_hash",
    )

    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)

    task = Task(
        title="TOM的任务",
        description=None,
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task.id,
        },
    )

    with pytest.raises(PendingActionNotFoundError):
        confirm_pending_action(
            session=db_session,
            action_id=action.id,
            owner_id=other_user.id,
        )


def test_cancel_action(
    db_session: Session,
    user: User,
) -> None:

    task = Task(
        title="不要删我",
        description=None,
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task.id,
        },
    )

    result = cancel_pending_action(
        session=db_session,
        action_id=action.id,
        owner_id=user.id,
    )

    assert result.status == "cancelled"

    existing_task = db_session.get(
        Task,
        task.id,
    )

    assert existing_task is not None


def test_cancelled_action_cannot_confirm(
    db_session: Session,
    user: User,
) -> None:

    task = Task(
        title="取消删除",
        description=None,
        status="pending",
        owner_id=user.id,
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    action = create_pending_action(
        session=db_session,
        owner_id=user.id,
        action="delete_task",
        payload={
            "task_id": task.id,
        },
    )

    cancel_pending_action(
        session=db_session,
        action_id=action.id,
        owner_id=user.id,
    )

    with pytest.raises(PendingActionAlreadyHandledError):
        confirm_pending_action(
            session=db_session,
            action_id=action.id,
            owner_id=user.id,
        )
