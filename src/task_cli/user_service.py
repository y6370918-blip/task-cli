from sqlalchemy.orm import Session

from task_cli.models import User
from task_cli.security import hash_password


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, email: str, password: str):

    user = User(username=username, email=email, password_hash=hash_password(password))

    db.add(user)

    db.commit()

    db.refresh(user)

    return user
