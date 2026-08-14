import type { Locale, LocaleMessageDictionary, VueI18n } from 'vue-i18n'

export const useI18n = () => {
  const nuxtApp = useNuxtApp()
  const $i18n = (nuxtApp as any).$i18n

  if ($i18n) {
    return $i18n as VueI18n<any, any, any, any> & {
      t: (key: string, ...args: any[]) => string
      locale: Ref<string>
      availableLocales: string[]
      setLocale?: (code: string) => Promise<void> | void
    }
  }

  // Safe fallback when i18n is not yet available (SSR startup edge case)
  const localeRef = ref('zh')
  const fallbackT = (key: string, ...args: any[]): string => {
    try {
      const parts = key.split('.')
      let val: any = {
        common: { submit: '提交', cancel: '取消', save: '保存', loading: '加载中...', login: '登录', logout: '登出', register: '注册', admin: '后台管理', posts: '文章', categories: '分类', tags: '标签', archive: '归档', viewAll: '查看全部', search: '搜索' } as Record<string, any>,
        auth: { login: '登录', logout: '登出', register: '注册' },
        post: { minutes: '分钟', share: '分享', passwordProtected: '文章已加密', enterPassword: '请输入密码', incorrectPassword: '密码错误', relatedPosts: '相关文章' },
        comment: { title: '评论', placeholder: '写下你的评论...', submit: '发表评论', loginToComment: '登录后参与评论', noComments: '暂无评论，来抢沙发吧！' },
        user: { profile: '个人资料', myPosts: '我的文章' },
        stats: { totalPosts: '文章总数', totalWords: '文字总数', totalCategories: '分类总数', totalTags: '标签总数' }
      }
      for (const part of parts) {
        if (val && typeof val === 'object' && part in val) {
          val = val[part]
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
  } as any
}

export const t = (key: string, ...args: any[]): string => {
  const nuxtApp = useNuxtApp()
  const $i18n = (nuxtApp as any).$i18n
  if ($i18n && typeof ($i18n as any).t === 'function') {
    return ($i18n as any).t(key, ...args)
  }
  return key
}

export type { Locale, LocaleMessageDictionary, VueI18n }
