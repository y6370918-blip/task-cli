import logging

from sqlalchemy.orm import Session

from task_cli.schemas import (
    TaskCreate,
    TaskUpdate,
)
from task_cli.services import (
    create_task,
    delete_task,
    list_tasks,
    update_task,
)

logger = logging.getLogger(__name__)


def show_menu() -> None:

    print(
        """
=====================
 Task CLI
=====================

1. 创建任务
2. 查看任务
3. 更新任务
4. 删除任务
5. 筛选任务
0. 退出

"""
    )


show_menu()


def handle_create_task(
    session: Session,
) -> None:

    title = input("请输入任务标题：")

    description = input("请输入任务描述：")

    data = TaskCreate(
        title=title,
        description=description or None,
    )

    task = create_task(
        session,
        data,
    )

    print(f"创建成功，任务ID：{task.id}")


def handle_list_tasks(
    session: Session,
) -> None:

    tasks = list_tasks(session)

    if not tasks:
        print("暂无任务")

        return

    for task in tasks:
        print(
            f"""
ID:{task.id}
标题：{task.title}
状态：{task.status}
描述：{task.description}
----------------
"""
        )


def handle_update_task(
    session: Session,
) -> None:

    try:
        task_id = int(input("请输入任务ID: "))

    except ValueError:
        print("请输入数字ID")

        return

    status = input("请输入新状态(pending/doing/done): ")

    data = TaskUpdate(status=status)

    task = update_task(
        session,
        task_id,
        data,
    )

    if task is None:
        print("任务不存在")

        return

    print("更新成功")


def handle_delete_task(
    session: Session,
) -> None:

    try:
        task_id = int(input("请输入任务ID: "))

    except ValueError:
        print("请输入数字ID")

        return

    result = delete_task(
        session,
        task_id,
    )

    if result:
        print("删除成功")

    else:
        print("任务不存在")


def run_cli(
    session: Session,
) -> None:

    while True:
        show_menu()

        choice = input("请选择: ")

        if choice == "1":
            handle_create_task(session)

        elif choice == "2":
            handle_list_tasks(session)

        elif choice == "3":
            handle_update_task(session)

        elif choice == "4":
            handle_delete_task(session)

        elif choice == "0":
            print("退出程序")

            break

        else:
            print("无效选择")
