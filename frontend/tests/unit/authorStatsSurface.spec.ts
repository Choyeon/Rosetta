/**
 * 批次 #148：作者统计的第二段消费方（`/authors/<username>` 读数行）。
 *
 * `GET /users/{user_id}/stats` 四个聚合投影齐全却从零消费方——主页只显示
 * 「N 篇文章」（那个数来自文章列表的 `total`）。接上以后有三条容易被顺手改坏的线：
 *
 * 1. **请求必须由页面发出，并且走 by-username 口**。页面按用户名寻址，接 by-id 口就要
 *    等资料回来再拼第二次请求的 URL，SSR 从并发变串行两跳。
 * 2. **数字不进 `toLocaleString` / `Intl`**。格式化结果依赖运行端 ICU 数据，服务端与
 *    浏览器不一致会在 hydration 那一刻打出文本差异（同页 `joinedLabel` 早已因此只取年份）。
 * 3. **零不显示**。「隐藏即空」是后端口径（开关关掉 → 该族归零），页面把 0 一起收起，
 *    空主页与藏了内容的主页才读起来一样。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const page = readFileSync(join(ROOT, 'pages', 'authors', '[username].vue'), 'utf-8')
const usersApi = readFileSync(join(REPO, 'backend', 'api', 'users.py'), 'utf-8')

function templateOf(source: string): string {
  const start = source.indexOf('<template>')
  const end = source.lastIndexOf('</template>')
  expect(start).toBeGreaterThanOrEqual(0)
  expect(end).toBeGreaterThan(start)
  return source.slice(start, end)
}

describe('统计请求真的接上了', () => {
  it('页面按用户名请求统计口（不是内部主键，也不是只写了个 ref）', () => {
    expect(page).toMatch(/useAPI<AuthorStats>\(\s*`\/users\/username\/\$\{username\.value\}\/stats`/)
  })

  it('后端确实声明了这条口（前端拼出来的路径不是凭空的）', () => {
    expect(usersApi).toContain('"/username/{username}/stats"')
  })

  it('缓存键带用户名与语言，避免跨作者/跨语言串数据', () => {
    expect(page).toContain('`author:stats:${username.value}:${locale.value}`')
  })

  it('失败态重试把第三个端点一起刷（漏一个就永远停在失败态）', () => {
    expect(page).toContain('Promise.all([refreshProfile(), refreshPosts(), refreshStats()])')
  })
})

describe('读数行把三个统计画出来', () => {
  const tpl = templateOf(page)

  it('三个 chip 都在 template 区，各自带 v-if 判零', () => {
    for (const key of ['totalViews', 'totalLikes', 'commentsCount']) {
      expect(tpl).toContain(`v-if="${key}"`)
      expect(tpl).toContain(`{{ ${key} }}`)
    }
  })

  it('标签走 i18n，不写死中文（四语键的存在由下面那组用例钉）', () => {
    expect(tpl).toContain('t(\'authors.views\'')
    expect(tpl).toContain('t(\'authors.likes\'')
    expect(tpl).toContain('t(\'authors.commentsCount\'')
  })

  it('图标取自 @lucide/vue 组件，不新增手抄 d=" 路径', () => {
    expect(page).toMatch(/import \{[^}]*Eye[^}]*ThumbsUp[^}]*\} from '@lucide\/vue'/)
    expect(tpl).not.toMatch(/\sd="M/)
  })

  it('数字原样输出，不碰 toLocaleString / Intl（SSR 与浏览器 ICU 不同版会打差异）', () => {
    expect(page).not.toMatch(/\.toLocaleString\(|Intl\.\w/)
  })

  it('统计挂了不把整页判成加载失败（它是读数装饰，不是主内容）', () => {
    expect(page).toContain('const loadError = computed(() => !!(profileError.value || postsErr.value))')
  })
})

describe('四语文案齐全', () => {
  const locales = ['zh', 'en', 'ja', 'zh_Hant']
  const keys = ['email', 'views', 'likes', 'commentsCount']

  it('四个语言文件都给了这批键（漏一语就是那一语的页面显示中文兜底）', () => {
    for (const locale of locales) {
      const dict = JSON.parse(readFileSync(join(ROOT, 'i18n', 'locales', `${locale}.json`), 'utf-8')) as {
        authors: Record<string, string>
      }
      for (const key of keys) {
        expect(dict.authors[key], `${locale}.authors.${key}`).toBeTruthy()
      }
    }
  })

  it('四个语言文件的 authors 键集合相等', () => {
    let baseline: string[] | null = null
    for (const locale of locales) {
      const dict = JSON.parse(readFileSync(join(ROOT, 'i18n', 'locales', `${locale}.json`), 'utf-8')) as {
        authors: Record<string, string>
      }
      const sorted = Object.keys(dict.authors).sort()
      if (baseline === null) {
        baseline = sorted
      } else {
        expect(sorted, locale).toEqual(baseline)
      }
    }
  })
})
