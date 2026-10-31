/**
 * 文章级音视频（`Post.audio` / `Post.video` / `Post.video_url`）的取值与校验单源。
 *
 * 后端写入口的同一份口径在 `backend/schemas/_url_policy.py::require_internal_media_path`
 * 与 `backend/schemas/_youtube.py::extract_youtube_id`：
 * - `audio` / `video` 只接受**站内路径**。CSP `media-src` 只有 `'self' blob: data:`
 *   （`backend/core/security_middleware.py` ↔ `deploy/nginx-site.conf` 两处同口径），
 *   外链会被浏览器拦掉——写入口不拒，作者看到的就是"保存成功、前台一个播放器都没有"。
 * - `video_url` 必须能解析出 YouTube 的 11 位 ID，渲染侧只用这个 ID 拼
 *   `youtube-nocookie.com/embed/<id>`（CSP `frame-src` 只放这一个域）。
 *   **绝不把库里的原始串拼进 iframe src**：导入 ZIP 与直连 SQL 都能塞进任意地址，
 *   那等于把任意站外页面嵌进访客的文章页。
 *
 * 判定原语复用 `lib/hero-media.ts`（轮播的视频档是同一条规则），避免两处漂移。
 */

import { extractYoutubeId, isSiteRelativeMediaUrl } from './hero-media'

/** 站内音视频地址；不合规回空串，调用方据此不渲染播放器。 */
export function internalMediaSrc(raw: string | null | undefined): string {
  const value = typeof raw === 'string' ? raw.trim() : ''
  return value && isSiteRelativeMediaUrl(value) ? value : ''
}

/**
 * 文章正文里的是"内容"不是"装饰背景"，所以和轮播那条不同：不自动播放、保留控制条。
 * 解析不出 ID 就回空串（整条不渲染），而不是退化成裸地址。
 */
export function youtubePlayerSrc(raw: string | null | undefined): string {
  const videoId = extractYoutubeId(raw)
  return videoId ? `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&playsinline=1` : ''
}

/**
 * 后台表单的提交前检查：让原因当场显示在字段上，而不是等后端 422 再弹一条 toast。
 * 空值合法（= 清掉），只有"填了但不合规"才报错。后端仍会再拦一次（写入口不止这一个）。
 */
export function postMediaErrors(form: {
  audio?: string | null
  video?: string | null
  video_url?: string | null
}): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const field of ['audio', 'video'] as const) {
    const value = (form[field] ?? '').trim()
    if (value && !isSiteRelativeMediaUrl(value)) {
      errors[field] = '必须是站内路径（如 /media/xxx.mp3），外链会被浏览器的 CSP 拦掉'
    }
  }
  const embed = (form.video_url ?? '').trim()
  if (embed && extractYoutubeId(embed) === null) {
    errors.video_url = '需要可解析出视频 ID 的 YouTube 地址（支持 watch?v= / youtu.be / embed / shorts）'
  }
  return errors
}
