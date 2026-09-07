import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  type ConversationItem,
  type PendingActionItem,
  cancelAssistantAction,
  confirmAssistantAction,
  getAssistantConversationMessages,
  listAssistantConversations,
  sendAssistantMessage,
} from "../api/assistant";
import { ApiError } from "../api/client";
import { formatDateTime } from "../utils/datetime";

type AssistantPanelProps = {
  accessToken: string;
  onUnauthorized: () => void;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type RequestStatus =
  | "idle"
  | "sending"
  | "confirming"
  | "cancelling"
  | "loading-conversations"
  | "loading-history";

type Feedback = {
  tone: "success" | "error";
  text: string;
};

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

  // 列表数据与当前打开的会话分别保存。
  // 刷新列表不会自动切换当前会话。
  const [conversations, setConversations] = useState<ConversationItem[]>([]);

  // 区分“还没查询”和“查询成功但没有会话”。
  // 两种情况下 conversations 都可能是空数组。
  const [hasLoadedConversations, setHasLoadedConversations] = useState(false);
  // useRef 保存跨渲染的值，但修改 .current 不会触发重新渲染。
  // 它能立即记录请求已开始，补充 state 更新之前的重复点击检查。
  const requestInFlight = useRef(false);

  // 本页成功追加消息时递增。
  // 不是数据库编号，也不会发送给后端。
  const nextLocalTurnId = useRef(1);
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

  const hasDraft = draft.trim() !== "";

  // 切换和新建都不能静默丢弃草稿或当前确认卡片。
  const canSwitchConversation = !busy && pendingAction === null && !hasDraft;

  const canSend =
    !busy &&
    pendingAction === null &&
    !conversationUnavailable &&
    messageLength > 0 &&
    messageLength <= 1000;

  async function handleLoadConversations(): Promise<void> {
    // 读取列表也复用请求锁，
    // 避免与发送消息或确认操作同时进行。
    if (requestInFlight.current || pendingAction !== null) {
      return;
    }

    requestInFlight.current = true;
    setRequestStatus("loading-conversations");
    setFeedback(null);

    try {
      const items = await listAssistantConversations(accessToken);

      // 用户退出后，不再用旧请求更新这个组件。
      if (!mounted.current) {
        return;
      }

      setConversations(items);
      setHasLoadedConversations(true);

      // 这里只更新列表。
      // 不修改当前会话编号、聊天消息或草稿。
    } catch (error: unknown) {
      if (!mounted.current) {
        return;
      }

      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized();
        return;
      }

      // 失败时保留已有列表和当前对话。
      // 不把请求失败伪装成“查询成功但没有会话”。
      setFeedback({
        tone: "error",
        text: getErrorMessage(error, "读取会话列表失败，请稍后重试。"),
      });
    } finally {
      // 成功或失败都释放锁，允许用户进行下一次操作。
      requestInFlight.current = false;

      if (mounted.current) {
        setRequestStatus("idle");
      }
    }
  }
  async function handleSelectConversation(targetId: number): Promise<void> {
    // disabled 控制按钮是否可点击，函数内部仍保留检查。
    if (requestInFlight.current || !canSwitchConversation) {
      return;
    }

    requestInFlight.current = true;
    setRequestStatus("loading-history");
    setFeedback(null);

    try {
      const history = await getAssistantConversationMessages(
        accessToken,
        targetId,
      );

      if (!mounted.current) {
        return;
      }

      // : ChatMessage 是回调函数的返回类型标注。
      // 每条历史消息转换成组件需要的显示对象。
      const historyMessages = history.map(
        (message): ChatMessage => ({
          id: `history-${message.id}`,
          role: message.role,
          content: message.content,
        }),
      );

      // 读取和校验成功后，才一并更新编号和消息。
      // 加载过程中仍保留原会话，避免编号与内容错配。
      setConversationId(targetId);
      setMessages(historyMessages);
      setDraft("");
      setConversationUnavailable(false);

      // 不从历史文字恢复 pendingAction，
      // 也不重新执行历史中的工具调用。
      setFeedback({
        tone: "success",
        text: `已读取会话 #${targetId} 的 ${history.length} 条可见历史消息，可继续对话。`,
      });
    } catch (error: unknown) {
      if (!mounted.current) {
        return;
      }

      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized();
        return;
      }

      // 只有不可用的是当前会话，才禁止继续向它发送。
      // 打开 B 失败，不能连原本可用的 A 也一起禁用。
      if (
        error instanceof ApiError &&
        error.status === 404 &&
        targetId === conversationId
      ) {
        setConversationUnavailable(true);
      }

      // 不清空 messages，不修改 conversationId，不自动重试。
      setFeedback({
        tone: "error",
        text:
          `读取会话 #${targetId} 失败：` +
          getErrorMessage(error, "请稍后重试。") +
          " 当前显示的对话已保留。",
      });
    } finally {
      requestInFlight.current = false;

      if (mounted.current) {
        setRequestStatus("idle");
      }
    }
  }

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

      // 在事件处理流程中分配编号。
      // 不在渲染或 state 更新函数内部增加计数。
      const localTurnId = nextLocalTurnId.current;
      nextLocalTurnId.current += 1;

      // history- 与 local- 前缀不同，不会发生编号碰撞。
      //
      // 更新函数只根据 previous 返回新数组，
      // 不修改旧数组，也不增加计数器。
      setMessages((previous) => [
        ...previous,
        {
          id: `local-${localTurnId}-user`,
          role: "user",
          content: submittedMessage,
        },
        {
          id: `local-${localTurnId}-assistant`,
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
          text: "当前会话不可用，输入已保留。请先处理草稿，再选择其他会话或新建会话。",
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
    // 与打开历史会话使用相同的切换条件。
    if (requestInFlight.current || !canSwitchConversation) {
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
          disabled={!canSwitchConversation}
          onClick={handleNewConversation}
        >
          新会话
        </button>
      </div>

      <p className="assistant-help">
        可以查询、创建和修改任务。删除任务需要点击下方确认按钮。
      </p>
      <section
        className="assistant-history"
        aria-labelledby="assistant-history-title"
      >
        <div className="assistant-history-heading">
          <h3 id="assistant-history-title">我的会话</h3>

          <button
            type="button"
            className="secondary-button"
            disabled={busy || pendingAction !== null}
            onClick={() => {
              // 箭头函数确保只在点击时调用，
              // 不在渲染时发送请求。
              //
              // void 表示这里不使用 Promise 返回值；
              // 请求错误已经在函数内部处理。
              void handleLoadConversations();
            }}
          >
            {requestStatus === "loading-conversations"
              ? "读取中……"
              : "刷新会话列表"}
          </button>
        </div>

        <p className="assistant-help">
          按创建时间倒序排列。新会话发送第一条消息后，可刷新列表查看。
        </p>

        {!hasLoadedConversations && (
          <p className="assistant-help">点击“刷新会话列表”读取你的历史会话。</p>
        )}

        {hasLoadedConversations && conversations.length === 0 && (
          <p className="assistant-help">当前账号还没有历史会话。</p>
        )}

        {hasLoadedConversations && conversations.length > 0 && (
          <ul className="assistant-history-list">
            {conversations.map((conversation) => (
              // 使用数据库中的会话 ID 标识列表项，
              // 不使用数组下标。
              <li key={conversation.id}>
                <strong>会话 #{conversation.id}</strong>

                {/* 原样显示时间，后续再统一处理时区显示。 */}
                <p className="assistant-history-time">
                  创建时间：{formatDateTime(conversation.createdAt)}
                </p>

                <button
                  type="button"
                  className="secondary-button"
                  disabled={!canSwitchConversation}
                  aria-label={`打开会话 #${conversation.id}`}
                  onClick={() => {
                    void handleSelectConversation(conversation.id);
                  }}
                >
                  {conversationId === conversation.id
                    ? "重新加载当前会话"
                    : "打开会话"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="assistant-help">
        打开会话时读取最近 50 条可见消息。
        历史文字不代表任务或操作的当前状态，也不会恢复删除确认卡片。
      </p>

      {hasDraft && (
        <p className="assistant-help">
          输入框有未发送草稿，请先处理草稿，再切换或新建会话。
          不想发送时，可以自行保存后清空。
        </p>
      )}

      {messages.length === 0 ? (
        <p className="assistant-empty">
          {conversationId === null
            ? "例如：查询我的高优先级任务。"
            : "这个会话没有可显示的历史消息，可以继续发送。"}
        </p>
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
            {formatDateTime(pendingAction.expiresAt)}
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
          {requestStatus === "loading-history"
            ? "正在读取历史消息，当前会话尚未切换……"
            : requestStatus === "loading-conversations"
              ? "正在读取会话列表……"
              : requestStatus === "sending"
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
          disabled={busy || pendingAction !== null}
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
