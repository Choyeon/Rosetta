/**
 * 文章「来源 / 原文出处」读写两端契约。
 *
 * 此前的形状是"半接通"：`Post.source` / `source_url` 两列在库里、schema 收、
 * 三个读口都回显、导入导出还会搬运，但后台编辑器表单从不发送、前台文章页从不渲染
 * ——于是这一列只对数据库存在。本文件钉住接通之后的三件事：
 *
 * 1. 展示口径（默认「原创」不占位、非 http(s) 的出处绝不进 href）——行为级测试。
 * 2. 编辑器真的把两个字段发出去，并且**回填**（不回填 = 改一次标题就把出处清掉）。
 * 3. 文章页把值渲染出来，外链带 rel 护栏。
 *
 * 静态核对那两条读的是源文本：先确认写法可行再断言，别改被测代码去迁就断言。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, it, expect } from 'vitest'
import { DEFAULT_POST_SOURCE, resolvePostSource } from '~~/lib/post-source'

const formSrc = readFileSync(resolve(process.cwd(), 'components/admin/PostForm.vue'), 'utf8')
const detailSrc = readFileSync(resolve(process.cwd(), 'pages/posts/[slug].vue'), 'utf8')

describe('来源展示口径（lib/post-source）', () => {
  it('默认「原创」且没有出处链接 → 整项不出现', () => {
    expect(resolvePostSource('原创', null)).toEqual({ visible: false, text: '', href: '' })
    expect(resolvePostSource('原创', '')).toEqual({ visible: false, text: '', href: '' })
    expect(resolvePostSource(null, null).visible).toBe(false)
  })

  it('非默认来源即使没有链接也要出现', () => {
    expect(resolvePostSource('少数派', '')).toEqual({
      visible: true,
      text: '少数派',
      href: ''
    })
  })

  it('来源是默认值但填了出处 → 用出处主机名当文本', () => {
    const view = resolvePostSource(DEFAULT_POST_SOURCE, 'https://www.example.com/a/b')
    expect(view.visible).toBe(true)
    expect(view.href).toBe('https://www.example.com/a/b')
    expect(view.text).toBe('example.com')
  })

  it('伪协议不当链接：javascript:/data:/协议相对都降级成"无链接"', () => {
    for (const bad of [
      'javascript:alert(document.cookie)',
      'data:text/html,<script>alert(1)</script>',
      '//evil.example/x',
      'sspai.com/post/1'
    ]) {
      const view = resolvePostSource('转载', bad)
      expect(view.href, `${bad} 不该成为 href`).toBe('')
      // 来源文本还在，只是不可点：不能因为链接脏就把整项藏掉
      expect(view.visible).toBe(true)
      expect(view.text).toBe('转载')
    }
  })

  it('http 与 https 都算合法（大小写无关）', () => {
    expect(resolvePostSource('转载', 'HTTP://example.com/x').href).toBe('HTTP://example.com/x')
    expect(resolvePostSource('转载', 'https://example.com/x').href).toBe('https://example.com/x')
  })
})

describe('后台编辑器：来源写入口', () => {
  it('表单状态含两个字段，且默认值是原创（列 NOT NULL）', () => {
    expect(formSrc).toContain('source: \'原创\',')
    expect(formSrc).toContain('source_url: \'\',')
  })

  it('回填已存值：不回填则每次 PUT 把出处提交成空', () => {
    expect(formSrc).toMatch(/form\.source = data\.source/)
    expect(formSrc).toMatch(/form\.source_url = data\.source_url/)
  })

  it('提交时始终发送，空出处归 null（省略键在 exclude_unset 下清不掉）', () => {
    expect(formSrc).toContain('source: form.source.trim() || \'原创\',')
    expect(formSrc).toContain('source_url: form.source_url.trim() || null,')
  })

  it('出处链接在前端也拦一次伪协议，并把错误显示在字段上', () => {
    expect(formSrc).toContain('const sourceUrlError = computed(')
    // 与 lib/post-source 同一把 scheme 闸门：写口拦住了，渲染侧还得再判一次
    expect(formSrc).toContain('/^https?:\\/\\//i.test(url)')
    expect(formSrc).toContain('if (srcErr) {')
    expect(formSrc).toContain(':error="sourceUrlError || undefined"')
  })

  it('两个控件都有 id 与后端同长的 maxlength', () => {
    for (const id of ['post-form-source', 'post-form-source-url']) {
      expect(formSrc, `缺少控件 #${id}`).toContain(`id="${id}"`)
    }
    expect(formSrc).toContain('maxlength="50"')
    expect(formSrc).toContain('maxlength="500"')
  })
})

describe('前台文章页：来源渲染', () => {
  it('走 lib/post-source 单源口径，不再自写一套判定', () => {
    expect(detailSrc).toContain('import { resolvePostSource } from \'~~/lib/post-source\'')
    expect(detailSrc).toContain('const sourceView = computed(() => resolvePostSource(')
    expect(detailSrc).toContain('v-if="sourceView.visible"')
  })

  it('外链带 noopener/noreferrer，且 nofollow 不给转载出处传权重', () => {
    expect(detailSrc).toContain('rel="noopener noreferrer nofollow"')
    expect(detailSrc).toContain('target="_blank"')
  })

  it('响应式模型类型声明了这两列（否则读的是 never、PUT 也写不进去）', () => {
    const apiTypes = readFileSync(resolve(process.cwd(), 'types/api.ts'), 'utf8')
    // Post（读）与 PostCreate（写）各一份，少一份就是某一端在类型层面写不出来
    expect([...apiTypes.matchAll(/\bsource\?: string/g)].length).toBe(2)
    expect([...apiTypes.matchAll(/source_url\?: string \| null/g)].length).toBe(2)
  })
})

describe('四语标签齐备', () => {
  for (const code of ['zh', 'en', 'ja', 'zh_Hant']) {
    it(`post.source 在 ${code} 有非空文案`, () => {
      const raw = readFileSync(resolve(process.cwd(), `i18n/locales/${code}.json`), 'utf8')
      const value = JSON.parse(raw).post?.source
      expect(typeof value, `i18n/locales/${code}.json 缺 post.source`).toBe('string')
      expect((value as string).trim()).not.toBe('')
    })
  }
})
