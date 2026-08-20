from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from task_cli.action_exceptions import (
    PendingActionAlreadyHandledError,
    PendingActionExpiredError,
    PendingActionNotFoundError,
)
from task_cli.exceptions import (
    TaskNotFoundError,
)
from task_cli.models import (
    PendingAction,
    Task,
)

def ensure_utc(
    value: datetime,
) -> datetime:
    """
    确保 datetime 是 UTC aware datetime。

    SQLite 读取 DateTime(timezone=True) 时，
    可能丢失 tzinfo，因此这里统一补成 UTC。
    """

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )

def create_pending_action(
    session: Session,
    owner_id: int,
    action: str,
    payload: dict,
    expires_minutes: int = 10,
) -> PendingAction:
    print(
        "ACTION DB:",
        session.get_bind().url.render_as_string(
        hide_password=True
        ),
    )
    now = datetime.now(
        timezone.utc
    )

    pending_action = PendingAction(
        owner_id=owner_id,
        action=action,
        payload=payload,
        status="pending",
        created_at=now,
        expires_at=(
            now
            + timedelta(
                minutes=expires_minutes
            )
        ),
    )

    session.add(
        pending_action
    )

    session.commit()
    session.refresh(
        pending_action
    )

    return pending_action

def confirm_pending_action(
    session: Session,
    action_id: int,
    owner_id: int,
) -> PendingAction:

    statement = select(
        PendingAction
    ).where(
        PendingAction.id == action_id,
        PendingAction.owner_id == owner_id,
    )

    pending_action = session.scalar(
        statement
    )

    if pending_action is None:
        raise PendingActionNotFoundError(
            f"操作 {action_id} 不存在"
        )

    if pending_action.status != "pending":
        raise PendingActionAlreadyHandledError(
            f"操作 {action_id} 已经被处理"
        )

    now = datetime.now(
        timezone.utc
    )

    expires_at = ensure_utc(
    pending_action.expires_at
)

    if expires_at < now:

        pending_action.status = "expired"

        session.commit()

        raise PendingActionExpiredError(
            f"操作 {action_id} 已经过期"
        )

    if pending_action.action == "delete_task":

        task_id = pending_action.payload[
            "task_id"
        ]

        task_statement = select(
            Task
        ).where(
            Task.id == task_id,
            Task.owner_id == owner_id,
        )

        task = session.scalar(
            task_statement
        )

        if task is None:
            raise TaskNotFoundError(
                task_id
            )

        session.delete(
            task
        )

        pending_action.status = (
            "confirmed"
        )

        pending_action.completed_at = now

        session.commit()

        session.refresh(
            pending_action
        )

        return pending_action

    raise ValueError(
        f"不支持的 action: "
        f"{pending_action.action}"
    )

def cancel_pending_action(
    session: Session,
    action_id: int,
    owner_id: int,
) -> PendingAction:

    statement = select(
        PendingAction
    ).where(
        PendingAction.id == action_id,
        PendingAction.owner_id == owner_id,
    )

    pending_action = session.scalar(
        statement
    )

    if pending_action is None:
        raise PendingActionNotFoundError(
            f"操作 {action_id} 不存在"
        )

    if pending_action.status != "pending":
        raise PendingActionAlreadyHandledError(
            f"操作 {action_id} 已经被处理"
        )

    now = datetime.now(
        timezone.utc
    )

    expires_at = ensure_utc(
        pending_action.expires_at
    )

    if expires_at < now:
        pending_action.status = "expired"

        session.commit()

        raise PendingActionExpiredError(
            f"操作 {action_id} 已经过期"
        )

    pending_action.status = "cancelled"

    pending_action.completed_at = now

    session.commit()
    session.refresh(
        pending_action
    )
    print(
        "PENDING ACTION CREATED:",
        pending_action.id,
        pending_action.owner_id,
        pending_action.action,
)
    return pending_action
