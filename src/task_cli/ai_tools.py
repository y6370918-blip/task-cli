import json
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from task_cli.action_service import create_pending_action
from task_cli.ai_exceptions import AIToolError
from task_cli.exceptions import TaskNotFoundError
from task_cli.schemas import (
    TaskUpdate,
)
from task_cli.schemas_ai import (
    CreateTaskToolArguments,
    ListTasksToolArguments,
    RequestDeleteTaskToolArguments,
    UpdateTaskToolArguments,
)
from task_cli.services import create_task, get_task, list_tasks, update_task

# =========================================================
# DeepSeek 可以使用的工具定义
# =========================================================

TOOLS = [
    # -----------------------------------------------------
    # 1. 查询任务
    # -----------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": (
                "查询当前登录用户自己的任务。"
                "可以按状态、优先级或是否逾期过滤。"
                "当用户询问自己的任务、待办事项、"
                "任务状态、任务优先级，或者要求总结任务时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "doing",
                            "done",
                        ],
                        "description": (
                            "可选的任务状态过滤条件。"
                            "pending 表示待处理，"
                            "doing 表示进行中，"
                            "done 表示已完成。"
                        ),
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                        ],
                        "description": (
                            "可选的任务优先级过滤条件。"
                            "low 表示低优先级，"
                            "medium 表示中优先级，"
                            "high 表示高优先级。"
                        ),
                    },
                    "overdue": {
                        "type": "boolean",
                        "description": (
                            "是否只查询已经逾期但尚未完成的任务。"
                            "设置为 true 时，只返回截止时间已过且状态不是 done 的任务。"
                            "未提供时默认为 false。"
                        ),
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    # -----------------------------------------------------
    # 2. 创建任务
    # -----------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": (
                "为当前登录用户创建一个新的任务。"
                "可以指定任务优先级和截止时间。"
                "任务会自动属于当前登录用户，"
                "不需要也不能提供 owner_id。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "任务标题。",
                    },
                    "description": {
                        "type": "string",
                        "description": "任务的详细描述，可选。",
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                        ],
                        "description": ("任务优先级，可选。未提供时默认为 medium。"),
                    },
                    "due_at": {
                        "type": "string",
                        "description": (
                            "任务截止时间，可选。"
                            "必须使用包含时区的 ISO 8601 时间，"
                            "例如 2026-09-01T18:00:00+08:00。"
                            "如果用户只提供模糊或相对时间，"
                            "必须先要求用户补充明确日期和时区。"
                        ),
                    },
                },
                "required": [
                    "title",
                ],
                "additionalProperties": False,
            },
        },
    },
    # -----------------------------------------------------
    # 3. 修改任务
    # -----------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": (
                "修改当前登录用户自己的任务。"
                "可以修改标题、描述、任务状态、优先级或者截止时间。"
                "不能修改其他用户的任务。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "需要修改的任务 ID。",
                    },
                    "title": {
                        "type": "string",
                        "description": "新的任务标题。",
                    },
                    "description": {
                        "type": "string",
                        "description": "新的任务描述。",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "doing",
                            "done",
                        ],
                        "description": ("新的任务状态：pending、doing 或 done。"),
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                        ],
                        "description": "新的任务优先级。",
                    },
                    "due_at": {
                        "anyOf": [
                            {
                                "type": "string",
                            },
                            {
                                "type": "null",
                            },
                        ],
                        "description": (
                            "新的任务截止时间。"
                            "设置时间时必须使用包含时区的 ISO 8601 时间，"
                            "例如 2026-09-01T18:00:00+08:00。"
                            "传入 null 表示清除原截止时间。"
                            "如果用户只提供模糊或相对时间，"
                            "必须先要求用户补充明确日期和时区。"
                        ),
                    },
                },
                "required": [
                    "task_id",
                ],
                "additionalProperties": False,
            },
        },
    },
    # -----------------------------------------------------
    # 4. 请求删除任务
    # -----------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "request_delete_task",
            "description": (
                "请求删除当前用户的某个任务。"
                "这是危险操作，此工具不会真正删除任务，"
                "只会要求用户进一步确认。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "准备删除的任务 ID。",
                    },
                },
                "required": [
                    "task_id",
                ],
                "additionalProperties": False,
            },
        },
    },
]


# =========================================================
# Tool 执行器
# =========================================================


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    db: Session,
    owner_id: int,
) -> str:
    """
    执行 DeepSeek 请求调用的工具。

    name:
        DeepSeek 想调用的工具名称。

    arguments:
        DeepSeek 为工具生成的参数。

    db:
        SQLAlchemy Session。

    owner_id:
        当前登录用户的 ID。
        这个值必须来自 JWT / current_user，
        不能由 DeepSeek 自己决定。
    """

    try:
        # =================================================
        # list_tasks
        # =================================================

        if name == "list_tasks":
            data = ListTasksToolArguments.model_validate(arguments)

            tasks = list_tasks(
                session=db,
                owner_id=owner_id,
                status=data.status,
                priority=data.priority,
                overdue=data.overdue,
            )

            result = {
                "success": True,
                "action": "list_tasks",
                "count": len(tasks),
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status,
                        "priority": task.priority,
                        "due_at": (
                            task.due_at.isoformat() if task.due_at is not None else None
                        ),
                    }
                    for task in tasks
                ],
                "message": (
                    "任务查询成功。"
                    "请根据这些真实数据回答用户，"
                    "不需要为了确认结果再次调用 list_tasks。"
                ),
            }

            return json.dumps(
                result,
                ensure_ascii=False,
            )

        # =================================================
        # create_task
        # =================================================

        if name == "create_task":
            data = CreateTaskToolArguments.model_validate(arguments)

            task = create_task(
                db,
                data,
                owner_id,
            )

            result = {
                "success": True,
                "action": "create_task",
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "due_at": (
                        task.due_at.isoformat() if task.due_at is not None else None
                    ),
                },
                "message": (
                    "任务创建成功。"
                    "可以直接把创建结果告诉用户，"
                    "不要重复调用 create_task。"
                ),
            }

            return json.dumps(
                result,
                ensure_ascii=False,
            )

        # =================================================
        # update_task
        # =================================================

        if name == "update_task":
            # 先使用严格的 Tool 参数模型验证：
            # - task_id 必须大于 0；
            # - priority 只能是 low/medium/high；
            # - owner_id 等额外字段会被拒绝。
            tool_data = UpdateTaskToolArguments.model_validate(arguments)

            # task_id 只负责定位任务，
            # 不能作为任务字段传给 Service 更新。
            task_id = tool_data.task_id

            # 排除 task_id，只保留模型实际要求修改的字段。
            update_fields = tool_data.model_dump(
                exclude={
                    "task_id",
                },
                exclude_unset=True,
            )

            # 如果模型只提供 task_id，
            # 实际上没有任何需要修改的内容。
            if not update_fields:
                raise AIToolError("没有提供需要修改的任务字段。")

            # 转换成 Service 真正需要的 TaskUpdate。
            data = TaskUpdate.model_validate(update_fields)

            # owner_id 仍然来自当前认证用户，
            # 不允许由 AI Tool 参数决定。
            task = update_task(
                session=db,
                task_id=task_id,
                data=data,
                owner_id=owner_id,
            )

            result = {
                "success": True,
                "action": "update_task",
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "due_at": (
                        task.due_at.isoformat() if task.due_at is not None else None
                    ),
                },
                "message": (
                    "任务修改成功。"
                    "请直接把修改结果告诉用户，"
                    "不要再次调用相同的 update_task。"
                ),
            }

            return json.dumps(
                result,
                ensure_ascii=False,
            )

        # =================================================
        # request_delete_task
        # =================================================

        if name == "request_delete_task":
            data = RequestDeleteTaskToolArguments.model_validate(arguments)

            task_id = data.task_id

            get_task(
                session=db,
                task_id=task_id,
                owner_id=owner_id,
            )

            pending_action = create_pending_action(
                session=db,
                owner_id=owner_id,
                action="delete_task",
                payload={
                    "task_id": task_id,
                },
            )

            result = {
                "success": True,
                "requires_confirmation": True,
                "action": "delete_task",
                "confirmation_id": (pending_action.id),
                "task_id": task_id,
                "expires_at": (pending_action.expires_at.isoformat()),
                "message": (
                    f"删除任务 {task_id} "
                    f"需要用户确认。"
                    f"确认操作编号为 "
                    f"{pending_action.id}。"
                ),
            }

            return json.dumps(
                result,
                ensure_ascii=False,
            )

        # =================================================
        # 未知 Tool
        # =================================================

        raise AIToolError(f"不支持的 AI 工具: {name}")

    # =====================================================
    # Pydantic 参数验证失败
    # =====================================================

    except ValidationError as exc:
        raise AIToolError(f"工具参数验证失败: {exc}") from exc

    # =====================================================
    # Task 不存在
    #
    # 这里也同时承担一个安全作用：
    # 如果 task_id 存在，但不属于当前 owner_id，
    # Service 应该同样表现为“找不到任务”。
    # =====================================================

    except TaskNotFoundError as exc:
        raise AIToolError(f"任务不存在，或者当前用户无权访问该任务: {exc}") from exc

    # =====================================================
    # 参数自身有问题
    # =====================================================

    except (KeyError, TypeError, ValueError) as exc:
        raise AIToolError(f"工具参数错误: {exc}") from exc
