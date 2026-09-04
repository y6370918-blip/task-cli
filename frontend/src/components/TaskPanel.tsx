import { type FormEvent, useState } from "react";

import { ApiError } from "../api/client";
import {
  type TaskCreateInput,
  type TaskItem,
  type TaskPriority,
  type TaskStatus,
  type TaskUpdateInput,
  createTask,
  deleteTask,
  listTasks,
  updateTask,
} from "../api/tasks";
import { TaskForm } from "./TaskForm";

type LoadStatus = "idle" | "loading" | "success" | "error";

type OperationStatus = "idle" | "submitting";

type OperationTone = "idle" | "loading" | "success" | "error";

type EditorState =
  | {
      mode: "closed";
    }
  | {
      mode: "create";
    }
  | {
      mode: "edit";
      task: TaskItem;
    };

type TaskPanelProps = {
  accessToken: string;

  // 只有请求明确返回 401 时才调用。
  // App 收到通知后负责清除整个 authSession。
  onUnauthorized: () => void;
};

const statusLabels: Record<TaskStatus, string> = {
  pending: "待处理",
  doing: "进行中",
  done: "已完成",
};

const priorityLabels: Record<TaskPriority, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

function readStatusFilter(value: string): TaskStatus | "" {
  // select 的 value 在 DOM 类型中只是 string。
  // 这里再次缩小范围，不使用不安全的类型断言。
  if (
    value === "" ||
    value === "pending" ||
    value === "doing" ||
    value === "done"
  ) {
    return value;
  }

  return "";
}

function readPriorityFilter(value: string): TaskPriority | "" {
  if (
    value === "" ||
    value === "low" ||
    value === "medium" ||
    value === "high"
  ) {
    return value;
  }

  return "";
}

function formatDateTime(value: string | null): string {
  if (value === null) {
    return "未设置";
  }

  // tasks.ts 已验证这是可以解析的时间字符串。
  // 浏览器在这里按用户本机区域显示。
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function TaskPanel({ accessToken, onUnauthorized }: TaskPanelProps) {
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "">("");

  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | "">("");

  const [tasks, setTasks] = useState<TaskItem[]>([]);

  const [loadStatus, setLoadStatus] = useState<LoadStatus>("idle");

  const [message, setMessage] = useState("选择筛选条件，然后查询任务。");

  const [editor, setEditor] = useState<EditorState>({
    mode: "closed",
  });

  const [operationStatus, setOperationStatus] =
    useState<OperationStatus>("idle");

  const [operationTone, setOperationTone] = useState<OperationTone>("idle");

  const [operationMessage, setOperationMessage] = useState("");

  const [deleteCandidate, setDeleteCandidate] = useState<TaskItem | null>(null);

  const busy = loadStatus === "loading" || operationStatus === "submitting";

  function handleUnauthorizedError(error: unknown): boolean {
    if (error instanceof ApiError && error.status === 401) {
      // 401 表示当前认证凭证已经不能继续使用。
      onUnauthorized();
      return true;
    }

    return false;
  }

  async function loadCurrentTasks(clearExisting: boolean): Promise<void> {
    setLoadStatus("loading");
    setMessage("正在查询任务……");

    if (clearExisting) {
      // 用户主动执行新查询时清除旧结果，
      // 避免旧筛选结果与新筛选条件同时显示。
      setTasks([]);
    }

    try {
      const result = await listTasks(accessToken, {
        status: statusFilter,
        priority: priorityFilter,
      });

      setTasks(result);
      setLoadStatus("success");
      setMessage(
        result.length === 0
          ? "当前条件下没有任务。"
          : `查询到 ${result.length} 条任务，最多显示 100 条。`,
      );
    } catch (error: unknown) {
      if (handleUnauthorizedError(error)) {
        return;
      }

      // 写操作后的刷新失败时没有清除旧列表，
      // 因此用户仍能看到刷新前的数据。
      setLoadStatus("error");
      setMessage(getErrorMessage(error, "任务查询失败，请重试。"));
    }
  }

  async function handleLoadTasks(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (busy) {
      return;
    }

    setOperationTone("idle");
    setOperationMessage("");

    await loadCurrentTasks(true);
  }

  async function handleCreateTask(input: TaskCreateInput): Promise<void> {
    if (operationStatus === "submitting") {
      return;
    }

    setOperationStatus("submitting");
    setOperationTone("loading");
    setOperationMessage("正在创建任务……");

    try {
      const createdTask = await createTask(accessToken, input);

      // 写操作成功后关闭编辑器。
      // 随后重新查询，因为新任务可能不符合当前筛选条件。
      setEditor({
        mode: "closed",
      });
      setOperationTone("success");
      setOperationMessage(
        `任务 #${createdTask.id} 创建成功，列表已按当前筛选条件刷新。`,
      );

      await loadCurrentTasks(false);
    } catch (error: unknown) {
      if (handleUnauthorizedError(error)) {
        return;
      }

      setOperationTone("error");
      setOperationMessage(getErrorMessage(error, "任务创建失败，请重试。"));
    } finally {
      setOperationStatus("idle");
    }
  }

  async function handleUpdateTask(input: TaskUpdateInput): Promise<void> {
    if (editor.mode !== "edit" || operationStatus === "submitting") {
      return;
    }

    const taskId = editor.task.id;

    setOperationStatus("submitting");
    setOperationTone("loading");
    setOperationMessage(`正在修改任务 #${taskId}……`);

    try {
      const updatedTask = await updateTask(accessToken, taskId, input);

      setEditor({
        mode: "closed",
      });
      setOperationTone("success");
      setOperationMessage(
        `任务 #${updatedTask.id} 修改成功，列表已按当前筛选条件刷新。`,
      );

      await loadCurrentTasks(false);
    } catch (error: unknown) {
      if (handleUnauthorizedError(error)) {
        return;
      }

      setOperationTone("error");
      setOperationMessage(getErrorMessage(error, "任务修改失败，请重试。"));
    } finally {
      setOperationStatus("idle");
    }
  }

  async function handleConfirmDelete(): Promise<void> {
    if (deleteCandidate === null || operationStatus === "submitting") {
      return;
    }

    const taskId = deleteCandidate.id;

    setOperationStatus("submitting");
    setOperationTone("loading");
    setOperationMessage(`正在删除任务 #${taskId}……`);

    try {
      await deleteTask(accessToken, taskId);

      setDeleteCandidate(null);
      setOperationTone("success");
      setOperationMessage(`任务 #${taskId} 已删除，列表已按当前筛选条件刷新。`);

      await loadCurrentTasks(false);
    } catch (error: unknown) {
      if (handleUnauthorizedError(error)) {
        return;
      }

      setOperationTone("error");
      setOperationMessage(getErrorMessage(error, "任务删除失败，请重试。"));
    } finally {
      setOperationStatus("idle");
    }
  }

  return (
    <section
      className="task-panel feature-card"
      aria-labelledby="task-panel-title"
    >
      <div className="task-panel-heading">
        <div>
          <p className="section-label">My Tasks</p>

          <h2 id="task-panel-title">我的任务</h2>
        </div>

        <div className="task-panel-heading-actions">
          <p className="task-limit">最多显示 100 条</p>

          <button
            type="button"
            className="connection-button task-create-button"
            disabled={busy}
            onClick={() => {
              setDeleteCandidate(null);
              setEditor({
                mode: "create",
              });
              setOperationTone("idle");
              setOperationMessage("");
            }}
          >
            创建任务
          </button>
        </div>
      </div>

      {editor.mode === "create" && (
        <TaskForm
          // key 让每次重新打开创建表单时
          // 都获得一组全新的本地 state。
          key="create-task"
          mode="create"
          submitting={operationStatus === "submitting"}
          onSubmit={handleCreateTask}
          onCancel={() => {
            setEditor({
              mode: "closed",
            });
          }}
        />
      )}

      {editor.mode === "edit" && (
        <TaskForm
          // 切换到不同任务时 key 会变化，
          // React 会重新创建表单并加载对应初始值。
          key={`edit-task-${editor.task.id}`}
          mode="edit"
          task={editor.task}
          submitting={operationStatus === "submitting"}
          onSubmit={handleUpdateTask}
          onCancel={() => {
            setEditor({
              mode: "closed",
            });
          }}
        />
      )}

      {deleteCandidate !== null && (
        <div
          className="task-delete-confirmation"
          role="alertdialog"
          aria-labelledby="delete-task-title"
        >
          <h3 id="delete-task-title">确认删除任务 #{deleteCandidate.id}</h3>

          <p>“{deleteCandidate.title}”删除后无法从当前应用中恢复。</p>

          <p>这是前端本地确认；确认后 REST API 会立即执行删除。</p>

          <div className="task-editor-actions">
            <button
              type="button"
              className="danger-button"
              disabled={operationStatus === "submitting"}
              onClick={() => {
                void handleConfirmDelete();
              }}
            >
              {operationStatus === "submitting" ? "删除中……" : "确认删除"}
            </button>

            <button
              type="button"
              className="secondary-button"
              disabled={operationStatus === "submitting"}
              onClick={() => {
                setDeleteCandidate(null);
              }}
            >
              取消
            </button>
          </div>
        </div>
      )}

      {operationMessage !== "" && (
        <p
          className={`task-operation-message task-operation-message--${operationTone}`}
          role="status"
        >
          {operationMessage}
        </p>
      )}

      <form className="task-filters" onSubmit={handleLoadTasks}>
        <label htmlFor="task-status-filter">状态</label>

        <select
          id="task-status-filter"
          name="status"
          value={statusFilter}
          disabled={busy}
          onChange={(event) => {
            setStatusFilter(readStatusFilter(event.target.value));
          }}
        >
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="doing">进行中</option>
          <option value="done">已完成</option>
        </select>

        <label htmlFor="task-priority-filter">优先级</label>

        <select
          id="task-priority-filter"
          name="priority"
          value={priorityFilter}
          disabled={busy}
          onChange={(event) => {
            setPriorityFilter(readPriorityFilter(event.target.value));
          }}
        >
          <option value="">全部优先级</option>
          <option value="low">低</option>
          <option value="medium">中</option>
          <option value="high">高</option>
        </select>

        <button type="submit" className="connection-button" disabled={busy}>
          {loadStatus === "loading" ? "查询中……" : "查询任务"}
        </button>
      </form>

      <p className={`task-message task-message--${loadStatus}`} role="status">
        {message}
      </p>

      {tasks.length > 0 && (
        <div className="task-list">
          {tasks.map((task) => (
            <article className="task-card" key={task.id}>
              <div className="task-card-heading">
                <div>
                  <p className="task-id">任务 #{task.id}</p>

                  <h3>{task.title}</h3>
                </div>

                <div className="task-badges">
                  <span className={`task-badge task-status--${task.status}`}>
                    {statusLabels[task.status]}
                  </span>

                  <span
                    className={`task-badge task-priority--${task.priority}`}
                  >
                    优先级：
                    {priorityLabels[task.priority]}
                  </span>
                </div>
              </div>

              <p className="task-description">
                {task.description ?? "暂无任务描述。"}
              </p>

              <dl className="task-metadata">
                <div>
                  <dt>截止时间</dt>
                  <dd>{formatDateTime(task.dueAt)}</dd>
                </div>

                <div>
                  <dt>创建时间</dt>
                  <dd>{formatDateTime(task.createdAt)}</dd>
                </div>
              </dl>

              <div className="task-card-actions">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => {
                    setDeleteCandidate(null);
                    setEditor({
                      mode: "edit",
                      task,
                    });
                    setOperationTone("idle");
                    setOperationMessage("");
                  }}
                >
                  编辑
                </button>

                <button
                  type="button"
                  className="danger-button"
                  disabled={busy}
                  onClick={() => {
                    // 打开删除确认时关闭编辑表单，
                    // 避免页面同时存在两个写操作入口。
                    setEditor({
                      mode: "closed",
                    });
                    setDeleteCandidate(task);
                    setOperationTone("idle");
                    setOperationMessage("");
                  }}
                >
                  删除
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
