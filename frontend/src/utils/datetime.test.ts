import { describe, expect, test } from "vitest";

import { formatDateTime } from "./datetime";

// describe：把同一个功能的测试放在一组。
// test：定义一个测试。
// expect(...).toBe(...)：断言实际值与预期值相同。
describe("formatDateTime", () => {
  test("没有时间时显示未设置", () => {
    expect(formatDateTime(null, "UTC")).toBe("未设置");
  });

  test("拒绝不符合时间格式的字符串", () => {
    expect(formatDateTime("not-a-date", "UTC")).toBe("时间格式不合法");
  });

  test("拒绝外形符合规则但无法解析的时间", () => {
    // 13 月无法构成有效时间。
    // 这与上一条测试覆盖的是不同检查分支。
    expect(formatDateTime("2026-13-01T12:00:00Z", "UTC")).toBe(
      "时间格式不合法",
    );
  });

  test("无时区时间保持原文，不擅自补充时区", () => {
    const value = "2026-09-01T12:00:00";
    const expected = `${value}（未提供时区，未转换）`;

    // 即使要求不同的显示时区，也不能猜测原始时间属于哪里。
    expect(formatDateTime(value, "UTC")).toBe(expected);
    expect(formatDateTime(value, "Asia/Shanghai")).toBe(expected);
  });

  test("同一时间点的不同偏移表示得到相同显示结果", () => {
    const utcValue = "2026-09-01T04:00:00Z";
    const shanghaiValue = "2026-09-01T12:00:00+08:00";

    expect(formatDateTime(utcValue, "Asia/Shanghai")).toBe(
      formatDateTime(shanghaiValue, "Asia/Shanghai"),
    );
  });

  test("按上海时区显示 UTC 时间", () => {
    const result = formatDateTime("2026-09-01T04:00:00Z", "Asia/Shanghai");

    // 不绑定日期分隔符等本地化细节，
    // 但要检查实际转换后的小时和明确的时区标签。
    expect(result).toContain("12:00:00");
    expect(result).toContain("（Asia/Shanghai）");
  });

  test("按 UTC 显示带有东八区偏移的时间", () => {
    const result = formatDateTime("2026-09-01T12:00:00+08:00", "UTC");

    expect(result).toContain("04:00:00");
    expect(result).toContain("（UTC）");
  });
});
