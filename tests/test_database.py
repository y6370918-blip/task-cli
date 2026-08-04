from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from task_cli.models import Base, Task


def test_create_task():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        task = Task(title="测试数据库")

        session.add(task)

        session.commit()

        assert task.id == 1
