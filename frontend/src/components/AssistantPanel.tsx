import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  type PendingActionItem,
  cancelAssistantAction,
  confirmAssistantAction,
  sendAssistantMessage,
} from "../api/assistant";
import { ApiError } from "../api/client";

type AssistantPanelProps = {
  accessToken: string;
  onUnauthorized: () => void;
};

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
};

type RequestStatus = "idle" | "sending" | "confirming" | "cancelling";

type Feedback = {
  tone: "success" | "error";
  text: string;
};

function formatExpiry(value: string): string {
  // API Client 已经验证时间字符串包含时区。
  // 显示时转换为浏览器所在地区的本地时间。
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function AssistantPanel({
  accessToken,
  onUnauthorized,
}: AssistantPanelProps) {
  const [draft, setDraft] = useState("");

  const [conversationId, setConversationId] = useState<number | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [pendingAction, setPendingAction] = useState<PendingActionItem | null>(
    null,
  );

  const [requestStatus, setRequestStatus] = useState<RequestStatus>("idle");

  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const [conversationUnavailable, setConversationUnavailable] = useState(false);

  // useRef 保存跨渲染的值，但修改 .current 不会触发重新渲染。
  // 它能立即记录请求已开始，补充 state 更新之前的重复点击检查。
  const requestInFlight = useRef(false);

  // 记录当前组件是否仍在页面中。
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;

    // 返回的函数会在组件卸载时执行。
    // 例如退出登录后，旧请求不能再通过回调影响新的登录状态。
    return () => {
      mounted.current = false;
    };
  }, []);

  // 上面的 Effect 只管理生命周期，不发送 AI 请求。
  // 真正的请求只由用户提交表单或点击按钮触发。
  const busy = requestStatus !== "idle";
  const messageLength = Array.from(draft.trim()).length;

  const canSend =
    !busy &&
    pendingAction === null &&
    !conversationUnavailable &&
    messageLength > 0 &&
    messageLength <= 1000;

  async function handleSend(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (requestInFlight.current || !canSend) {
      return;
    }

    // 保存本次提交的文本，供成功后追加到对话中。
    const submittedMessage = draft.trim();

    requestInFlight.current = true;
    setRequestStatus("sending");
    setFeedback(null);

    try {
      const result = await sendAssistantMessage(accessToken, {
        message: submittedMessage,
        conversationId,
      });

      if (!mounted.current) {
        return;
      }

      setConversationId(result.conversationId);
      setPendingAction(result.pendingAction);

      // 函数式更新根据最新的 messages 追加内容，
      // 不直接修改旧数组。
      //
      // 本步骤只在拿到有效回复后追加这一轮对话。
      // 这些 ID 只用于本页列表，不是数据库 Message 的 ID。
      setMessages((previous) => [
        ...previous,
        {
          id: previous.length + 1,
          role: "user",
          content: submittedMessage,
        },
        {
          id: previous.length + 2,
          role: "assistant",
          content: result.reply,
        },
      ]);

      // 成功收到回复后才清空输入框。
      setDraft("");
    } catch (error: unknown) {
      if (!mounted.current) {
        return;
      }

      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized();
        return;
      }

      if (error instanceof ApiError && error.status === 404) {
        // 保留当前显示内容，不自动改成另一个会话。
        // 用户可以点击“新会话”明确开始新的对话。
        setConversationUnavailable(true);
        setFeedback({
          tone: "error",
          text: "当前会话不可用，请点击“新会话”后继续。",
        });
        return;
      }

      // 失败时保留 draft，不自动重发。
      // 后端可能已经保存消息，甚至完成了任务操作，
      // 因此不能把响应失败解释为“什么都没发生”。
      setFeedback({
        tone: "error",
        text:
          `${getErrorMessage(error, "未能取得 AI 回复。")}` +
          " 输入已保留；如果请求涉及任务变更，请先查询任务结果再决定是否重发。",
      });
    } finally {
      requestInFlight.current = false;

      if (mounted.current) {
        setRequestStatus("idle");
      }
    }
  }

  async function handleAction(decision: "confirm" | "cancel"): Promise<void> {
    const action = pendingAction;

    if (action === null || requestInFlight.current) {
      return;
    }

    requestInFlight.current = true;
    setRequestStatus(decision === "confirm" ? "confirming" : "cancelling");
    setFeedback(null);

    try {
      // 使用结构化结果中的 actionId。
      // 不读取用户输入，也不从回复文字中提取编号。
      const result =
        decision === "confirm"
          ? await confirmAssistantAction(accessToken, action.actionId)
          : await cancelAssistantAction(accessToken, action.actionId);

      if (!mounted.current) {
        return;
      }

      setPendingAction(null);
      setFeedback({
        tone: "success",
        text:
          result.status === "confirmed"
            ? `任务 #${action.taskId} 已删除，请在“我的任务”中重新查询。`
            : `已取消删除任务 #${action.taskId}。`,
      });
    } catch (error: unknown) {
      if (!mounted.current) {
        return;
      }

      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized();
        return;
      }

      if (
        error instanceof ApiError &&
        (error.status === 404 || error.status === 409 || error.status === 410)
      ) {
        // 这些状态表示本页不应继续确认这个操作。
        // 清除本地按钮不会修改数据库中的操作状态。
        //
        // 特别是 409，只能说明已经处理，
        // 不能据此声称任务已经删除。
        setPendingAction(null);
        setFeedback({
          tone: "error",
          text:
            `操作 #${action.actionId}：${error.message}。` +
            "请查询任务的当前状态。",
        });
        return;
      }

      // 网络异常或响应格式错误时保留操作卡片，
      // 不自动再次调用确认/取消接口。
      setFeedback({
        tone: "error",
        text:
          `${getErrorMessage(error, "操作处理失败。")}` +
          " 尚未确认处理结果，请先检查任务状态。",
      });
    } finally {
      requestInFlight.current = false;

      if (mounted.current) {
        setRequestStatus("idle");
      }
    }
  }

  function handleNewConversation(): void {
    if (requestInFlight.current || pendingAction !== null) {
      return;
    }

    // 这里只重置本页状态，不删除服务器上的旧会话。
    // 下一次发送消息时，conversationId 为 null，
    // 后端才会创建新会话。
    setConversationId(null);
    setMessages([]);
    setDraft("");
    setFeedback(null);
    setConversationUnavailable(false);
  }

  return (
    <section
      className="assistant-panel feature-card"
      aria-labelledby="assistant-title"
    >
      <div className="assistant-heading">
        <div>
          <p className="section-label">AI Assistant</p>

          <h2 id="assistant-title">AI 任务助手</h2>

          <p className="assistant-conversation">
            {conversationId === null
              ? "发送第一条消息开始对话"
              : `当前会话 #${conversationId}`}
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          disabled={busy || pendingAction !== null}
          onClick={handleNewConversation}
        >
          新会话
        </button>
      </div>

      <p className="assistant-help">
        可以查询、创建和修改任务。删除任务需要点击下方确认按钮。
      </p>

      {messages.length === 0 ? (
        <p className="assistant-empty">例如：查询我的高优先级任务。</p>
      ) : (
        <ol className="assistant-messages" role="log" aria-label="本页对话">
          {messages.map((message) => (
            <li
              key={message.id}
              className={`assistant-message assistant-message--${message.role}`}
            >
              <p className="assistant-message-role">
                {message.role === "user" ? "你" : "AI 助手"}
              </p>

              {/* React 会将字符串作为文本渲染。
                    不使用 dangerouslySetInnerHTML，
                    即使回复包含 HTML，也不会作为 HTML 执行。 */}
              <p className="assistant-message-content">{message.content}</p>
            </li>
          ))}
        </ol>
      )}

      {pendingAction !== null && (
        <section
          className="assistant-action"
          aria-labelledby="assistant-action-title"
        >
          <h3 id="assistant-action-title">
            确认删除任务 #{pendingAction.taskId}
          </h3>

          <p>操作编号：#{pendingAction.actionId}</p>

          <p>
            有效期至：
            {formatExpiry(pendingAction.expiresAt)}
          </p>

          <p>确认后将删除此任务。请先确认或取消，再继续对话。</p>

          <div className="assistant-action-buttons">
            <button
              type="button"
              className="danger-button"
              disabled={busy}
              onClick={() => {
                void handleAction("confirm");
              }}
            >
              {requestStatus === "confirming" ? "确认中……" : "确认删除"}
            </button>

            <button
              type="button"
              className="secondary-button"
              disabled={busy}
              onClick={() => {
                void handleAction("cancel");
              }}
            >
              {requestStatus === "cancelling" ? "取消中……" : "取消删除"}
            </button>
          </div>

          {/* 前端只显示过期时间。
                是否过期仍以服务器检查和 410 响应为准，
                不依赖用户电脑时钟来决定权限。 */}
        </section>
      )}

      {feedback !== null && (
        <p
          className={`assistant-feedback assistant-feedback--${feedback.tone}`}
          role={feedback.tone === "error" ? "alert" : "status"}
        >
          {feedback.text}
        </p>
      )}

      {busy && (
        <p className="assistant-loading" role="status">
          {requestStatus === "sending"
            ? "正在等待 AI 回复……"
            : "正在处理操作……"}
        </p>
      )}

      <form className="assistant-form" onSubmit={handleSend}>
        <label htmlFor="assistant-message-input">发送消息</label>

        <textarea
          id="assistant-message-input"
          name="message"
          rows={4}
          value={draft}
          disabled={busy || pendingAction !== null || conversationUnavailable}
          aria-describedby="assistant-message-length"
          onChange={(event) => {
            setDraft(event.target.value);
          }}
        />

        <p id="assistant-message-length">{messageLength} / 1000 个字符</p>

        <button type="submit" className="connection-button" disabled={!canSend}>
          {requestStatus === "sending" ? "发送中……" : "发送"}
        </button>
      </form>

      <p className="assistant-help">
        AI 修改任务后，请在“我的任务”中重新查询。 开始新会话不会删除以前的记录。
      </p>
    </section>
  );
}
