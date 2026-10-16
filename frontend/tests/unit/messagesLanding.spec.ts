/**
 * 私信（/api/messages*）落地契约（静态源码断言，不开浏览器）。
 *
 * 后端这一族 6 个端点就绪已久、前端零消费（见 frontend/docs/API_COVERAGE.md 的 messages 行），
 * 表现是「通知里说有人给你发了私信，但站内没有任何地方读」。2026-10-16 接成
 * /account/messages（会话列表 + 正文 + 撰写 + 整段标已读 + 未读角标）与作者主页的「发私信」。
 * 路径全部是字符串字面量，写错的实测表现是 405/404 而不是编译错误，所以这里钉住六条口径：
 * 1. useMessages 只导出真的有消费点的三个方法；按单条标已读（PUT /messages/{id}/read）
 *    刻意不包装 —— 读正文那条已经带副作用清掉整个会话的未读；
 * 2. 会话列表与正文走 useAPI（响应式 url/key/query），不得另造裸 $fetch；
 * 3. 正文只走 JSON 请求体：走 query string 会整条落进 nginx 访问日志（后端 5000 字上限）；
 * 4. 未读总数只认 GET /messages/unread/count：列表是分页的，把本页 unread_count 加总当成
 *    全站未读会少报；
 * 5. 读正文即置已读（后端副作用），所以正文到手必须回刷列表 + 角标，否则角标停在旧值；
 * 6. 登录态私有态：作者主页的入口包在 ClientOnly 里（SSR 期 auth store 是 skipHydrate，
 *    拿不到 token），且 /account/** 的 noindex 由页面自带。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const read = (p: string) => readFileSync(resolve(ROOT, p), 'utf-8')

const composable = read('composables/useMessages.ts')
const page = read('pages/account/messages.vue')
const author = read('pages/authors/[username].vue')
const header = read('components/AppHeader.vue')

const MESSAGE_KEYS = [
  'title', 'fromProfile', 'unreadTotal', 'markRead', 'empty', 'loadFailed',
  'selectHint', 'emptyThread', 'placeholder', 'send', 'sending', 'limit'
]

describe('useMessages 封装', () => {
  it.each([
    'getUnreadMessageCount',
    'sendPrivateMessage',
    'markConversationRead'
  ])('导出 %s（有真实消费点才允许出现在这一族里）', (name) => {
    expect(composable).toContain(`const ${name} =`)
    expect(composable.slice(composable.lastIndexOf('return {'))).toContain(name)
  })

  it('未读总数走静默口：轮询失败不该弹 toast', () => {
    expect(composable).toContain(
      'silentApiFetch<{ count: number }>(\'/messages/unread/count\')'
    )
  })

  it('发送把正文放进请求体而不是查询串', () => {
    expect(composable).toContain('apiFetch<MessageSendResult>(\'/messages\'')
    expect(composable).toContain('body: { recipient_id: recipientId, content }')
    expect(composable).not.toContain('query: { recipient_id')
  })

  it('整段标已读用 PUT /messages/read-all/{对端}，且不出现按单条标已读的形态', () => {
    expect(composable).toContain('`/messages/read-all/${peerId}`')
    expect(composable).toContain('method: \'PUT\'')
    expect(/\/messages\/\$\{[^}]+\}\/read(?![\w-])/.test(composable)).toBe(false)
  })
})

describe('/account/messages 页面', () => {
  it('列表与正文都走 useAPI 单源，URL 随分页/选中对端变化', () => {
    expect(page).toContain('useAPI<MessageConversationList>(\'/messages/conversations\'')
    expect(page).toContain('`/messages/${peerId.value ?? 0}`')
    expect(page).toContain('query: computed(() => ({ page: convPage.value, page_size: 20 }))')
    expect(page).not.toContain('$fetch(')
  })

  it('未选中对端时首轮不发正文请求', () => {
    expect(page).toContain('immediate: peerId.value != null')
    expect(page).toContain('watch: [peerId]')
  })

  it('读正文即置已读：正文到手后回刷列表与角标', () => {
    expect(page).toContain('watch(threadData')
    expect(page).toContain('void refreshConv()')
    expect(page).toContain('void loadUnread()')
  })

  it('角标来自未读总数端点，而不是把本页各会话的 unread_count 加总', () => {
    expect(page).toContain('typeof res?.count === ')
    expect(page).not.toContain('reduce((sum')
  })

  it('登录态私有页：档位由 routeRules 单源，页面自带 noindex', () => {
    expect(page).toContain('definePageMeta({ layout: \'default\', middleware: \'auth-required\' })')
    expect(/definePageMeta\([^)]*ssr/.test(page)).toBe(false)
    expect(page).toContain('useNoindexPage()')
  })

  it('选中态写进 ?to= 查询串，可分享、前进后退可用', () => {
    expect(page).toContain('query.to = String(value)')
    expect(page).toContain('router.replace({ query })')
  })
})

describe('入口', () => {
  it('顶栏桌面下拉与移动抽屉各有一个私信入口', () => {
    expect(header.split('navigateTo(\'/account/messages\')').length - 1).toBe(2)
  })

  it('作者主页入口只对「已登录 + 非本人」出现，且包在 ClientOnly 里', () => {
    expect(author).toContain('const canMessage = computed(() =>')
    expect(author).toContain('profile.value?.id !== authStore.user?.id')
    expect(author.indexOf('<ClientOnly>') < author.indexOf('v-if="canMessage"')).toBe(true)
    // 中性路径要过 applyLocalePrefix，否则英文页跳回中文前缀地址
    expect(author).toContain('applyLocalePrefix(`/account/messages?to=${profile.value?.id ?? 0}`')
  })
})

describe('四语键', () => {
  it.each(['zh', 'en', 'ja', 'zh_Hant'])('%s 补齐 messages.*', (code) => {
    const json = JSON.parse(read(`i18n/locales/${code}.json`)) as Record<string, Record<string, string>>
    expect(json.messages).toBeDefined()
    for (const key of MESSAGE_KEYS) {
      expect(json.messages?.[key], `messages.${key} 缺失于 ${code}`).toBeTruthy()
    }
  })
})
