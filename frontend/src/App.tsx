import "./App.css";

type Feature = {
  title: string;
  description: string;
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
  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">task-cli · Web Client</p>

        <h1 id="page-title">AI Task Assistant</h1>

        <p className="lead">
          为真实 FastAPI 后端建立的 React + TypeScript 前端。
        </p>

        <p className="status">
          Day51：前端骨架已建立，API 接入将在 Day52 完成。
        </p>
      </section>

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
