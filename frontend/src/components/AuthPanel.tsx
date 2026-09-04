import { type FormEvent, useState } from "react";

import {
  type AuthenticatedUser,
  getCurrentUser,
  loginUser,
  registerUser,
} from "../api/auth";

type AuthMode = "login" | "register";

type SubmitStatus = "idle" | "submitting" | "success" | "error";

type AuthPanelProps = {
  currentUser: AuthenticatedUser | null;

  // AuthPanel 不自己长期保存 Token。
  // 登录完成后，将验证过的用户和 Token 交给父组件 App。
  onAuthenticated: (user: AuthenticatedUser, accessToken: string) => void;

  onLogout: () => void;
};

export function AuthPanel({
  currentUser,
  onAuthenticated,
  onLogout,
}: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>("login");

  // 这些输入框都是“受控组件”：
  // 输入框的 value 来自 React state，
  // onChange 再将用户输入写回 state。
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [submitStatus, setSubmitStatus] = useState<SubmitStatus>("idle");

  const [message, setMessage] = useState("请登录或创建一个新账号。");

  function switchMode(nextMode: AuthMode): void {
    if (submitStatus === "submitting") {
      return;
    }

    setMode(nextMode);
    setSubmitStatus("idle");
    setMessage(
      nextMode === "login"
        ? "请输入用户名和密码。"
        : "请输入用户名、邮箱和密码。",
    );

    // 切换表单时清除密码，避免密码在不同操作之间残留。
    setPassword("");
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    // 浏览器默认会提交表单并刷新页面。
    // React 应用需要阻止刷新，由 JavaScript 调用 API。
    event.preventDefault();

    // 防止用户连续点击造成重复注册或重复登录请求。
    if (submitStatus === "submitting") {
      return;
    }

    setSubmitStatus("submitting");
    setMessage(mode === "login" ? "正在登录……" : "正在创建账号……");

    try {
      if (mode === "register") {
        const createdUser = await registerUser({
          username,
          email,
          password,
        });

        // 当前设计中注册成功不自动登录。
        // 回到登录模式，并保留用户名方便用户继续登录。
        setMode("login");
        setUsername(createdUser.username);
        setEmail("");
        setPassword("");
        setSubmitStatus("success");
        setMessage(`账号 ${createdUser.username} 注册成功，请输入密码登录。`);

        return;
      }

      // 第一步：用户名和密码换取 Token。
      const tokenResult = await loginUser({
        username,
        password,
      });

      // 第二步：使用 Token 查询当前用户。
      // 只有 /auth/me 验证成功后，才建立前端认证状态。
      const authenticatedUser = await getCurrentUser(tokenResult.accessToken);

      // 将 Token 和用户资料交给 App 保存。
      // 不将 Token 写入 localStorage、URL 或页面内容。
      onAuthenticated(authenticatedUser, tokenResult.accessToken);

      setPassword("");
      setSubmitStatus("success");
      setMessage("登录成功。");
    } catch (error: unknown) {
      setSubmitStatus("error");

      // API Client 的 ApiError 继承自 Error，
      // 因此这里可以读取经过控制的错误消息。
      setMessage(
        error instanceof Error ? error.message : "认证请求失败，请重试。",
      );
    }
  }

  if (currentUser !== null) {
    return (
      <section
        className="auth-panel feature-card"
        aria-labelledby="account-title"
      >
        <h2 id="account-title">当前账号</h2>

        <dl className="account-details">
          <div>
            <dt>用户 ID</dt>
            <dd>{currentUser.id}</dd>
          </div>

          <div>
            <dt>用户名</dt>
            <dd>{currentUser.username}</dd>
          </div>

          <div>
            <dt>邮箱</dt>
            <dd>{currentUser.email}</dd>
          </div>
        </dl>

        <button type="button" className="secondary-button" onClick={onLogout}>
          退出登录
        </button>
      </section>
    );
  }

  return (
    <section className="auth-panel feature-card" aria-labelledby="auth-title">
      <div className="auth-heading">
        <div>
          <p className="section-label">Authentication</p>
          <h2 id="auth-title">{mode === "login" ? "登录" : "创建账号"}</h2>
        </div>

        <div className="auth-tabs" aria-label="选择认证方式">
          <button
            type="button"
            className={
              mode === "login" ? "auth-tab auth-tab--active" : "auth-tab"
            }
            aria-pressed={mode === "login"}
            disabled={submitStatus === "submitting"}
            onClick={() => switchMode("login")}
          >
            登录
          </button>

          <button
            type="button"
            className={
              mode === "register" ? "auth-tab auth-tab--active" : "auth-tab"
            }
            aria-pressed={mode === "register"}
            disabled={submitStatus === "submitting"}
            onClick={() => switchMode("register")}
          >
            注册
          </button>
        </div>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="auth-username">用户名</label>
        <input
          id="auth-username"
          name="username"
          type="text"
          value={username}
          autoComplete="username"
          required
          minLength={mode === "register" ? 3 : undefined}
          maxLength={50}
          disabled={submitStatus === "submitting"}
          onChange={(event) => {
            setUsername(event.target.value);
          }}
        />

        {mode === "register" && (
          <>
            <label htmlFor="auth-email">邮箱</label>
            <input
              id="auth-email"
              name="email"
              type="email"
              value={email}
              autoComplete="email"
              required
              disabled={submitStatus === "submitting"}
              onChange={(event) => {
                setEmail(event.target.value);
              }}
            />
          </>
        )}

        <label htmlFor="auth-password">密码</label>
        <input
          id="auth-password"
          name="password"
          type="password"
          value={password}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          required
          minLength={mode === "register" ? 8 : undefined}
          maxLength={72}
          disabled={submitStatus === "submitting"}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />

        <button
          type="submit"
          className="connection-button"
          disabled={submitStatus === "submitting"}
        >
          {submitStatus === "submitting"
            ? "提交中……"
            : mode === "login"
              ? "登录"
              : "注册"}
        </button>
      </form>

      <p className={`auth-message auth-message--${submitStatus}`} role="status">
        {message}
      </p>
    </section>
  );
}
