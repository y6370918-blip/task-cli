from sqlalchemy import create_engine
from sqlalchemy.orm import Session


from task_cli.models import Base
from task_cli.schemas import TaskCreate
from task_cli.services import create_task, list_tasks


def test_create_task():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        task = create_task(session, TaskCreate(title="学习Service"))

        assert task.id == 1

        assert task.title == "学习Service"


def test_list_tasks():

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        create_task(session, TaskCreate(title="任务1"))

        tasks = list_tasks(session)

        assert len(tasks) == 1
