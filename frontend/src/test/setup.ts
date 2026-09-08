import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// afterEach：每个测试结束后执行。
// 类似 pytest Fixture 中用于清理的 yield 后半部分。
afterEach(() => {
  // 卸载测试渲染的 React 组件，并清理对应 DOM。
  // 防止上一个测试的按钮、输入框影响下一个测试。
  cleanup();

  // 恢复通过 vi.spyOn 替换的方法。
  vi.restoreAllMocks();

  // 恢复通过 vi.stubGlobal 替换的全局对象。
  // 后续测试会用它替换 fetch。
  vi.unstubAllGlobals();

  // 恢复通过 vi.stubEnv 修改的环境变量。
  // 后续测试会提供专用的 VITE_API_BASE_URL。
  vi.unstubAllEnvs();
});
