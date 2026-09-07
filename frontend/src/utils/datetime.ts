// 只接受当前后端使用的 ISO 日期时间外形。
//
// ^ 和 $：匹配整个字符串。
// \d：数字。
// {4}：重复 4 次。
// (?:...)：把规则组成一组，不提取匹配内容。
// ?：前面的部分可以省略。
// |：或者。
//
// 允许小数秒，也允许末尾暂时没有时区。
// 这是显示层的基本检查，不是完整的日期合法性验证。
const isoDateTimePattern =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$/;

// 单独判断末尾是否有明确的时区信息。
// [+-] 表示接受加号或减号。
// 接受 Z、+08:00、-05:00 等格式。
const timeZoneSuffixPattern = /(?:Z|[+-]\d{2}:\d{2})$/;

// export 让其他文件能够导入这个函数。
// resolvedOptions() 返回格式化器实际采用的配置。
// 在浏览器里，timeZone 例如 "Asia/Shanghai"。
export function getBrowserTimeZone(): string {
  return new Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// value 可以是时间字符串，也可以是 null。
//
// 第二个参数有默认值：页面通常不传，使用浏览器时区。
// 测试时可以显式传入 "UTC" 或 "Asia/Shanghai"，
// 避免测试结果依赖运行测试的电脑设置。
//
// timeZone 由程序提供有效时区名称，
// 不直接接收任意用户输入。
export function formatDateTime(
  value: string | null,
  timeZone: string = getBrowserTimeZone(),
): string {
  if (value === null) {
    return "未设置";
  }

  // test() 返回字符串是否匹配这个正则表达式。
  if (!isoDateTimePattern.test(value)) {
    return "时间格式不合法";
  }

  // 没有时区，就不知道它对应哪个确定的时间点。
  //
  // 必须在 new Date(value) 之前处理：
  // 不让 JavaScript 按本机时区猜测，也不擅自补 Z。
  if (!timeZoneSuffixPattern.test(value)) {
    return `${value}（未提供时区，未转换）`;
  }

  const date = new Date(value);

  // 无法解析的 Date，其 getTime() 返回 NaN。
  // 先检查，避免后面的 format() 因无效日期报错。
  if (Number.isNaN(date.getTime())) {
    return "时间格式不合法";
  }

  const formatted = new Intl.DateTimeFormat("zh-CN", {
    // 语言决定显示习惯；timeZone 决定按哪个时区显示。
    //
    // 对象属性简写：
    // timeZone 等价于 timeZone: timeZone。
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",

    // 使用 00 到 23 的小时表示，避免 AM/PM。
    hourCycle: "h23",
  }).format(date);

  // 模板字符串中的 ${...} 会插入表达式的值。
  // 明确显示时区名称，不只给用户一个没有上下文的时间。
  //
  // 这里只生成显示文字，不修改原始 value 或数据库。
  return `${formatted}（${timeZone}）`;
}
