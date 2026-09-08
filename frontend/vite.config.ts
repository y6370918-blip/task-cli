import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// 使用 vitest/config 的 defineConfig，
// 让 TypeScript 同时认识 Vite 配置和新增的 test 配置。
export default defineConfig({
  // 保留现有 React 插件，正常开发和构建仍然使用它。
  plugins: [react()],

  test: {
    // 提供 document、window 等模拟浏览器环境。
    // 后续 React 组件测试也使用这个环境。
    // 它不等于真实浏览器，不能证明页面布局正常。
    environment: "jsdom",

    // 每个测试文件执行前，先加载公共初始化文件。
    setupFiles: ["./src/test/setup.ts"],

    // 明确导入 test、expect 等函数，不使用隐式全局变量。
    globals: false,
  },
});
