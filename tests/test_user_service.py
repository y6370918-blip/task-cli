import pytest
from sqlalchemy.orm import Session

from task_cli.exceptions import UserAlreadyExistsError
from task_cli.schemas_user import UserCreate
from task_cli.security import verify_password
from task_cli.user_service import create_user


def test_create_user_hashes_password(
    db_session: Session,
) -> None:
    data = UserCreate(
        username="alice",
        email="alice@example.com",
        password="password123",
    )

    user = create_user(
        db_session,
        data,
    )

    assert user.id is not None
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.password_hash != data.password
    assert verify_password(
        data.password,
        user.password_hash,
    )


def test_create_user_rejects_duplicate_username(
    db_session: Session,
) -> None:
    create_user(
        db_session,
        UserCreate(
            username="alice",
            email="alice@example.com",
            password="password123",
        ),
    )

    duplicate = UserCreate(
        username="alice",
        email="different@example.com",
        password="different-password",
    )

    with pytest.raises(UserAlreadyExistsError):
        create_user(
            db_session,
            duplicate,
        )


def test_create_user_rejects_duplicate_email(
    db_session: Session,
) -> None:
    create_user(
        db_session,
        UserCreate(
            username="alice",
            email="alice@example.com",
            password="password123",
        ),
    )

    duplicate = UserCreate(
        username="different-user",
        email="alice@example.com",
        password="different-password",
    )

    with pytest.raises(UserAlreadyExistsError):
        create_user(
            db_session,
            duplicate,
        )
