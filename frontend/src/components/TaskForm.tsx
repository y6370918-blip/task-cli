import { type FormEvent, useState } from "react";

import {
  type TaskCreateInput,
  type TaskItem,
  type TaskPriority,
  type TaskStatus,
  type TaskUpdateInput,
} from "../api/tasks";

type CommonTaskFormProps = {
  submitting: boolean;
  onCancel: () => void;
};

type CreateTaskFormProps = CommonTaskFormProps & {
  mode: "create";
  onSubmit: (input: TaskCreateInput) => Promise<void>;
};

type EditTaskFormProps = CommonTaskFormProps & {
  mode: "edit";
  task: TaskItem;
  onSubmit: (input: TaskUpdateInput) => Promise<void>;
};

// mode 是判别字段。
// 当 mode 为 create 和 edit 时，
// TypeScript 会分别推断对应的 onSubmit 参数类型。
type TaskFormProps = CreateTaskFormProps | EditTaskFormProps;

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

function toDateTimeLocal(value: string | null): string {
  if (value === null) {
    return "";
  }

  const date = new Date(value);

  // datetime-local 不包含时区，
  // 因此必须使用本地时间的年月日等字段，
  // 不能直接使用 toISOString().slice(...)。
  return [
    date.getFullYear(),
    "-",
    padDatePart(date.getMonth() + 1),
    "-",
    padDatePart(date.getDate()),
    "T",
    padDatePart(date.getHours()),
    ":",
    padDatePart(date.getMinutes()),
    ":",
    padDatePart(date.getSeconds()),
  ].join("");
}

function toAwareDateTime(value: string): string | null {
  if (value === "") {
    return null;
  }

  // 浏览器将 datetime-local 的值解释为用户本机时间。
  // toISOString() 再把它转换为带 Z 时区标记的 UTC 时间。
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new Error("截止时间格式不合法。");
  }

  return date.toISOString();
}

function readTaskPriority(value: string): TaskPriority | null {
  if (value === "low" || value === "medium" || value === "high") {
    return value;
  }

  return null;
}

function readTaskStatus(value: string): TaskStatus | null {
  if (value === "pending" || value === "doing" || value === "done") {
    return value;
  }

  return null;
}

export function TaskForm(props: TaskFormProps) {
  const initialTask = props.mode === "edit" ? props.task : null;

  // 父组件之后会使用 key 控制表单重新挂载。
  // 因此这里不需要用 useEffect 同步 initialTask。
  const [title, setTitle] = useState(() => initialTask?.title ?? "");

  const [description, setDescription] = useState(
    () => initialTask?.description ?? "",
  );

  const [priority, setPriority] = useState<TaskPriority>(
    () => initialTask?.priority ?? "medium",
  );

  const [status, setStatus] = useState<TaskStatus>(
    () => initialTask?.status ?? "pending",
  );

  const [dueAtLocal, setDueAtLocal] = useState(() =>
    toDateTimeLocal(initialTask?.dueAt ?? null),
  );

  const [validationMessage, setValidationMessage] = useState("");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (props.submitting) {
      return;
    }

    const normalizedTitle = title.trim();

    if (normalizedTitle === "") {
      setValidationMessage("任务标题不能为空。");
      return;
    }

    const normalizedDescription =
      description.trim() === "" ? null : description.trim();

    let dueAt: string | null;

    try {
      dueAt = toAwareDateTime(dueAtLocal);
    } catch (error: unknown) {
      setValidationMessage(
        error instanceof Error ? error.message : "截止时间格式不合法。",
      );
      return;
    }

    setValidationMessage("");

    if (props.mode === "create") {
      await props.onSubmit({
        title: normalizedTitle,
        description: normalizedDescription,
        priority,
        dueAt,
      });

      return;
    }

    await props.onSubmit({
      title: normalizedTitle,
      description: normalizedDescription,
      status,
      priority,
      dueAt,
    });
  }

  const idPrefix =
    props.mode === "create" ? "create-task" : `edit-task-${props.task.id}`;

  return (
    <form className="task-editor" onSubmit={handleSubmit}>
      <div className="task-editor-heading">
        <div>
          <p className="section-label">
            {props.mode === "create"
              ? "Create Task"
              : `Edit Task #${props.task.id}`}
          </p>

          <h3>{props.mode === "create" ? "创建新任务" : "编辑任务"}</h3>
        </div>
      </div>

      <label htmlFor={`${idPrefix}-title`}>标题</label>

      <input
        id={`${idPrefix}-title`}
        name="title"
        type="text"
        value={title}
        required
        maxLength={100}
        disabled={props.submitting}
        onChange={(event) => {
          setTitle(event.target.value);
        }}
      />

      <label htmlFor={`${idPrefix}-description`}>描述</label>

      <textarea
        id={`${idPrefix}-description`}
        name="description"
        value={description}
        maxLength={500}
        rows={4}
        disabled={props.submitting}
        onChange={(event) => {
          setDescription(event.target.value);
        }}
      />

      <label htmlFor={`${idPrefix}-priority`}>优先级</label>

      <select
        id={`${idPrefix}-priority`}
        name="priority"
        value={priority}
        disabled={props.submitting}
        onChange={(event) => {
          const nextPriority = readTaskPriority(event.target.value);

          if (nextPriority !== null) {
            setPriority(nextPriority);
          }
        }}
      >
        <option value="low">低</option>
        <option value="medium">中</option>
        <option value="high">高</option>
      </select>

      {props.mode === "edit" && (
        <>
          <label htmlFor={`${idPrefix}-status`}>状态</label>

          <select
            id={`${idPrefix}-status`}
            name="status"
            value={status}
            disabled={props.submitting}
            onChange={(event) => {
              const nextStatus = readTaskStatus(event.target.value);

              if (nextStatus !== null) {
                setStatus(nextStatus);
              }
            }}
          >
            <option value="pending">待处理</option>
            <option value="doing">进行中</option>
            <option value="done">已完成</option>
          </select>
        </>
      )}

      <label htmlFor={`${idPrefix}-due-at`}>截止时间</label>

      <input
        id={`${idPrefix}-due-at`}
        name="dueAt"
        type="datetime-local"
        step="1"
        value={dueAtLocal}
        disabled={props.submitting}
        onChange={(event) => {
          setDueAtLocal(event.target.value);
        }}
      />

      <p className="task-editor-help">
        留空表示没有截止时间；编辑时清空会删除原截止时间。
      </p>

      {validationMessage !== "" && (
        <p className="task-editor-error" role="alert">
          {validationMessage}
        </p>
      )}

      <div className="task-editor-actions">
        <button
          type="submit"
          className="connection-button"
          disabled={props.submitting}
        >
          {props.submitting
            ? "保存中……"
            : props.mode === "create"
              ? "创建任务"
              : "保存修改"}
        </button>

        <button
          type="button"
          className="secondary-button"
          disabled={props.submitting}
          onClick={props.onCancel}
        >
          取消
        </button>
      </div>
    </form>
  );
}
