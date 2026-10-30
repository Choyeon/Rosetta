/**
 * 语言无关的文本比较（小写化后按码位序）。
 *
 * 刻意不用 localeCompare：它按运行时的 ICU 排序规则走，Node（SSR）与浏览器对
 * 中英混排给出相反的结果（实测「AI」vs「安全」两端顺序相反）。落在 ?sort=name
 * 这类可分享 URL 上，表现是首屏按 SSR 顺序渲染、任意一次交互后列表静默换序。
 * 码位比较不依赖 ICU，SSR 与 hydrate 逐字节一致。
 */
export const compareText = (a: string, b: string): number => {
  const x = a.toLowerCase()
  const y = b.toLowerCase()
  return x < y ? -1 : x > y ? 1 : 0
}
