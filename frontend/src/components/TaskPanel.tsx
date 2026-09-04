import { type FormEvent, useState } from "react";

import { ApiError } from "../api/client";
import {
  type TaskItem,
  type TaskPriority,
  type TaskStatus,
  listTasks,
} from "../api/tasks";

type LoadStatus = "idle" | "loading" | "success" | "error";

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

export function TaskPanel({ accessToken, onUnauthorized }: TaskPanelProps) {
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "">("");

  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | "">("");

  const [tasks, setTasks] = useState<TaskItem[]>([]);

  const [loadStatus, setLoadStatus] = useState<LoadStatus>("idle");

  const [message, setMessage] = useState("选择筛选条件，然后查询任务。");

  async function handleLoadTasks(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    // 阻止浏览器刷新页面，由 React 调用 Task API。
    event.preventDefault();

    if (loadStatus === "loading") {
      return;
    }

    setLoadStatus("loading");
    setTasks([]);
    setMessage("正在查询任务……");

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
      if (error instanceof ApiError && error.status === 401) {
        // 401 表示当前认证凭证不能继续使用。
        // 清除会话后，App 会卸载 TaskPanel 并恢复登录表单。
        onUnauthorized();
        return;
      }

      // 503、网络失败和响应格式错误不会自动退出登录。
      setLoadStatus("error");
      setMessage(
        error instanceof Error ? error.message : "任务查询失败，请重试。",
      );
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

        <p className="task-limit">最多显示 100 条</p>
      </div>

      <form className="task-filters" onSubmit={handleLoadTasks}>
        <label htmlFor="task-status-filter">状态</label>

        <select
          id="task-status-filter"
          name="status"
          value={statusFilter}
          disabled={loadStatus === "loading"}
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
          disabled={loadStatus === "loading"}
          onChange={(event) => {
            setPriorityFilter(readPriorityFilter(event.target.value));
          }}
        >
          <option value="">全部优先级</option>
          <option value="low">低</option>
          <option value="medium">中</option>
          <option value="high">高</option>
        </select>

        <button
          type="submit"
          className="connection-button"
          disabled={loadStatus === "loading"}
        >
          {loadStatus === "loading" ? "查询中……" : "查询任务"}
        </button>
      </form>

      <p className={`task-message task-message--${loadStatus}`} role="status">
        {message}
      </p>

      {loadStatus === "success" && tasks.length > 0 && (
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
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
