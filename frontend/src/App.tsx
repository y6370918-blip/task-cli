import { useState } from "react";

import { type AuthenticatedUser } from "./api/auth";
import { getReadiness } from "./api/health";
import { AuthPanel } from "./components/AuthPanel";
import "./App.css";

type Feature = {
  title: string;
  description: string;
};

type ConnectionStatus = "idle" | "loading" | "success" | "error";

type AuthSession = {
  // App 同时保存经过 /auth/me 验证的用户和原始 Token。
  // Day54 请求任务列表时会使用 accessToken。
  user: AuthenticatedUser;
  accessToken: string;
};

const features: Feature[] = [
  {
    title: "任务管理",
    description: "创建、查询、更新和删除属于当前用户的任务。",
  },
  {
    title: "安全隔离",
    description: "FastAPI 根据 JWT 识别用户，前端不能自行决定 owner_id。",
  },
  {
    title: "AI 助手",
    description: "通过受控的 Tool Calling 查询和管理任务。",
  },
];

function App() {
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("idle");

  const [connectionMessage, setConnectionMessage] =
    useState("尚未检查后端连接。");

  // null 表示当前页面没有已认证会话。
  // 这个状态只存在于内存中，刷新页面后会恢复为 null。
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);

  async function handleCheckConnection(): Promise<void> {
    if (connectionStatus === "loading") {
      return;
    }

    setConnectionStatus("loading");
    setConnectionMessage("正在检查 API 和数据库连接……");

    try {
      const result = await getReadiness();

      setConnectionStatus("success");
      setConnectionMessage(
        `后端状态：${result.status}。本次 API 响应和数据库查询成功。`,
      );
    } catch (error: unknown) {
      setConnectionStatus("error");
      setConnectionMessage(
        error instanceof Error
          ? `检查失败：${error.message}`
          : "检查失败，请重试。",
      );
    }
  }

  function handleAuthenticated(
    user: AuthenticatedUser,
    accessToken: string,
  ): void {
    // 只有 AuthPanel 完成登录并通过 /auth/me 后，
    // 才会调用这个函数建立认证状态。
    setAuthSession({
      user,
      accessToken,
    });
  }

  function handleLogout(): void {
    // 当前后端没有 Token 撤销接口。
    // 这里仅清除前端内存中的用户资料和 Token。
    setAuthSession(null);
  }

  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">task-cli · Web Client</p>

        <h1 id="page-title">AI Task Assistant</h1>

        <p className="lead">
          为真实 FastAPI 后端建立的 React + TypeScript 前端。
        </p>

        <p className="status">Day53：注册、登录与前端认证状态。</p>
      </section>

      <section
        className="connection-panel feature-card"
        aria-labelledby="connection-title"
      >
        <h2 id="connection-title">后端连接检查</h2>

        <p>请求 /health/ready，检查 API 是否响应以及数据库能否执行查询。</p>

        <button
          type="button"
          className="connection-button"
          onClick={handleCheckConnection}
          disabled={connectionStatus === "loading"}
        >
          {connectionStatus === "loading" ? "检查中……" : "检查后端连接"}
        </button>

        <p
          className={`connection-result connection-result--${connectionStatus}`}
          role="status"
        >
          {connectionMessage}
        </p>
      </section>

      <AuthPanel
        // 可选链 ?.：authSession 为 null 时不读取 user。
        // 空值合并 ??：左侧为 null 或 undefined 时使用 null。
        currentUser={authSession?.user ?? null}
        onAuthenticated={handleAuthenticated}
        onLogout={handleLogout}
      />

      <section className="feature-grid" aria-label="项目核心功能">
        {features.map((feature) => (
          <article className="feature-card" key={feature.title}>
            <h2>{feature.title}</h2>
            <p>{feature.description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}

export default App;
