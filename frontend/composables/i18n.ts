/**
 * i18n 辅助层（存在理由 = SSR 启动竞态下的安全兜底）。
 *
 * 自动导入实测优先级（见 .nuxt/imports.d.ts）：本文件的 `t` 会覆盖全局自动导入，
 * 而本文件的 `useI18n` 会被 @nuxtjs/i18n 的同名自动导入顶掉——调用方拿到的
 * `useI18n()` 始终是官方实例，不要依赖本文件导出的 useI18n 做常规取实例。
 *
 * 这里的降级路径只服务一个场景：`$i18n` 尚未注入 nuxtApp 的 SSR 启动边缘调用。
 * 兜底字典是**仅中文**的最小集（不是真 i18n），命中不了 key 时原样返回 key，
 * 目的是保证不抛错、不阻塞首字节渲染——不要在业务代码里主动依赖兜底文案。
 */
import type { Locale, LocaleMessageDictionary, VueI18n } from 'vue-i18n'

/** nuxtApp 上由 @nuxtjs/i18n 注入的 $i18n */
interface NuxtAppWithI18n {
  $i18n?: unknown
}

type I18nInstance = VueI18n & {
  t: (key: string, ...args: unknown[]) => string
  tm: (key: string) => string
  locale: Ref<string>
  availableLocales: string[]
  setLocale?: (code: string) => Promise<void> | void
}

export const useI18n = (): I18nInstance => {
  const nuxtApp = useNuxtApp()
  const $i18n = (nuxtApp as NuxtAppWithI18n).$i18n

  if ($i18n) {
    return $i18n as I18nInstance
  }

  // Safe fallback when i18n is not yet available (SSR startup edge case)
  const localeRef = ref('zh')
  const fallbackT = (key: string, ..._args: unknown[]): string => {
    try {
      const parts = key.split('.')
      let val: unknown = {
        common: { submit: '提交', cancel: '取消', save: '保存', loading: '加载中...', login: '登录', logout: '登出', register: '注册', admin: '后台管理', posts: '文章', categories: '分类', tags: '标签', archive: '归档', viewAll: '查看全部', search: '搜索' } as Record<string, unknown>,
        auth: { login: '登录', logout: '登出', register: '注册' },
        post: { minutes: '分钟', share: '分享', passwordProtected: '文章已加密', enterPassword: '请输入密码', incorrectPassword: '密码错误', relatedPosts: '相关文章' },
        comment: { title: '评论', placeholder: '写下你的评论...', submit: '发表评论', loginToComment: '登录后参与评论', noComments: '暂无评论，来抢沙发吧！' },
        user: { profile: '个人资料', myPosts: '我的文章' },
        stats: { totalPosts: '文章总数', totalWords: '文字总数', totalCategories: '分类总数', totalTags: '标签总数' }
      }
      for (const part of parts) {
        if (val && typeof val === 'object' && part in val) {
          val = (val as Record<string, unknown>)[part]
        } else {
          return key
        }
      }
      return typeof val === 'string' ? val : key
    } catch {
      return key
    }
  }

  return {
    t: fallbackT,
    locale: localeRef,
    availableLocales: ['zh', 'zh_Hant', 'en', 'ja'],
    messages: {},
    fallbackLocale: 'en'
  } as unknown as I18nInstance
}

export const t = (key: string, ...args: unknown[]): string => {
  const nuxtApp = useNuxtApp()
  const $i18n = (nuxtApp as NuxtAppWithI18n).$i18n
  if ($i18n && typeof ($i18n as { t?: unknown }).t === 'function') {
    return ($i18n as { t: (key: string, ...args: unknown[]) => string }).t(key, ...args)
  }
  return key
}

export type { Locale, LocaleMessageDictionary, VueI18n }
