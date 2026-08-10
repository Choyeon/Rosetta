import { createHash } from "crypto-js";

const GRAVATAR_CDN = "https://www.gravatar.com/avatar/";
const GRAVATAR_MIRROR = "https://cravatar.cn/avatar/";
const QQ_AVATAR_API = "https://q1.qlogo.cn/g?b=qq&nk=";

type Fallback = "404" | "mp" | "identicon" | "monsterid" | "wavatar" | "retro" | "robohash" | "blank";

/**
 * 将邮箱 / QQ 号解析为头像 URL。
 * 邮箱 → Gravatar（附带 default fallback），纯数字 → QQ 头像。
 *
 * @param identifier 邮箱、QQ 号或任意字符串
 * @param options.size 尺寸 px（Gravatar 生效）
 * @param options.fallback Gravatar fallback 策略
 * @param options.useMirror 国内用 cravatar.cn 镜像提速
 */
export function resolveAvatar(
  identifier: string | null | undefined,
  options: { size?: number; fallback?: Fallback; useMirror?: boolean } = {}
): string {
  const { size = 128, fallback = "mp", useMirror = true } = options;
  const id = (identifier || "").trim();

  if (!id) {
    return `${useMirror ? GRAVATAR_MIRROR : GRAVATAR_CDN}00000000000000000000000000000000?s=${size}&d=${fallback}`;
  }

  if (/^\d{5,12}$/.test(id)) {
    const s = Math.min(640, Math.max(1, size));
    return `${QQ_AVATAR_API}${encodeURIComponent(id)}&s=${s}`;
  }

  const isEmail = /^[\w.+-]+@[\w-]+\.[\w.-]+$/.test(id);
  const hashSource = isEmail ? id.toLowerCase() : id;
  const md5 = createHash("md5").update(hashSource).toString();
  const base = useMirror ? GRAVATAR_MIRROR : GRAVATAR_CDN;
  return `${base}${md5}?s=${size}&d=${fallback}&r=g`;
}

/**
 * 生成默认头像列表（用户上传失败 / 未设置头像时的快捷选项）。
 * 返回尺寸为 size 的 Gravatar 默认策略组合。
 */
export function defaultAvatarPresets(size = 128): Array<{ label: Fallback; url: string }> {
  const presets: Fallback[] = ["mp", "identicon", "monsterid", "wavatar", "retro", "robohash"];
  return presets.map(p => ({
    label: p,
    url: `${GRAVATAR_CDN}00000000000000000000000000000000?s=${size}&d=${p}&f=y`,
  }));
}
