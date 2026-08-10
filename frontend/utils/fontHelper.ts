/**
 * 字体加载助手：把 FontFace / document.fonts.ready 包成 Promise，
 * 便于在页面首次渲染前「等字体就绪后再计算排版」，避免 CLS。
 */

export interface FontLoadOptions {
  family: string;
  weight?: number | string;
  style?: string;
  timeoutMs?: number;
}

/**
 * 等指定字体 family 被浏览器判定 ready。
 * - 服务端 / 无 `document.fonts` 时立即 resolve（SSR 安全）
 * - 超时后 resolve 不抛错，调用方可选是否降级
 */
export function waitForFontReady(opts: FontLoadOptions): Promise<boolean> {
  const { family, weight = "400", style = "normal", timeoutMs = 3000 } = opts;
  if (!import.meta.client) return Promise.resolve(false);
  if (typeof (document as Document & { fonts?: FontFaceSet }).fonts === "undefined") {
    return Promise.resolve(false);
  }
  const descriptor = `${weight} ${style} 1em "${family}"`;
  const fonts = document.fonts;
  const loadPromise = Promise.resolve(fonts.load ? fonts.load(descriptor) : fonts.ready).then(() => {
    if (fonts.check?.(descriptor)) return true;
    return fonts.ready.then(() => !!fonts.check?.(descriptor));
  });
  const timeoutPromise = new Promise<boolean>(res => setTimeout(() => res(false), timeoutMs));
  return Promise.race([loadPromise, timeoutPromise]).catch(() => false);
}

/**
 * 一次性等「系统关键字体全部就绪」后返回。
 * 用于 `onNuxtReady` 钩子，避免首屏字体切换造成的抖动。
 */
export function waitForCriticalFonts(
  families: string[],
  timeoutMs = 4000
): Promise<boolean[]> {
  return Promise.all(families.map(f => waitForFontReady({ family: f, timeoutMs })));
}

/**
 * 判断是否使用了「等宽字体」（根据 fontFamily 字符串粗略识别，代码块 TOC 计算宽度时用）。
 */
export function looksLikeMonospace(fontFamily: string): boolean {
  const lower = fontFamily.toLowerCase();
  return (
    lower.includes("mono") ||
    lower.includes("consolas") ||
    lower.includes("menlo") ||
    lower.includes("source code") ||
    lower.includes("fira code") ||
    lower.includes("jetbrains mono") ||
    lower.includes("cascadia") ||
    lower.includes("monospace")
  );
}
