from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from task_cli.exceptions import UserAlreadyExistsError
from task_cli.models import User
from task_cli.schemas_user import UserCreate
from task_cli.security import hash_password


def get_user_by_username(
    session: Session,
    username: str,
) -> User | None:
    statement = select(User).where(User.username == username)

    return session.scalar(statement)


def create_user(
    session: Session,
    data: UserCreate,
) -> User:
    statement = select(User).where(
        or_(
            User.username == data.username,
            User.email == str(data.email),
        )
    )

    existing_user = session.scalar(statement)

    if existing_user is not None:
        raise UserAlreadyExistsError

    user = User(
        username=data.username,
        email=str(data.email),
        password_hash=hash_password(data.password),
    )

    try:
        session.add(user)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise UserAlreadyExistsError from exc

    session.refresh(user)

    return user
