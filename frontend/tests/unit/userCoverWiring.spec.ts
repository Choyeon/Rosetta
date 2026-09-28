/**
 * 用户封面图（User.cover_image）接线契约（静态扫描，不开浏览器）。
 *
 * 这个字段后端一直存在（PUT /users/me 可写、UserResponse 可读、作者资料变更会失效
 * 文章缓存），但前端此前**既不写也不读**——头像能换、封面换不了，作者主页永远光板。
 * 本 spec 钉住三件容易在重构中静默失效的事：
 * 1. 设置页必须真的把 cover_image 随 PUT /users/me 提交，且清空时写 **null 而不是 ''**
 *    （后端 model_dump(exclude_unset=True)：显式 null 落 SQL NULL，'' 会留下一条假封面值）；
 * 2. 上传必须走 useMediaUploadCover（POST /media/cover），不得裸用 $fetch；
 * 3. 两处展示位（个人中心 / 作者主页）都得有 v-if 兜底——没封面时不能渲染 <img>，
 *    否则会打出破图；装饰图 alt 必须为空，作者名已在相邻标题里。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const settings = readFileSync(resolve(process.cwd(), 'pages/account/settings.vue'), 'utf8')
const account = readFileSync(resolve(process.cwd(), 'pages/account/index.vue'), 'utf8')
const author = readFileSync(resolve(process.cwd(), 'pages/authors/[username].vue'), 'utf8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'].map(loc => JSON.parse(
  readFileSync(resolve(process.cwd(), `i18n/locales/${loc}.json`), 'utf8')
) as Record<string, Record<string, string>>)

describe('pages/account/settings.vue 封面写入', () => {
  it('上传走 useMediaUploadCover，且经由 apiFetch 封装（不裸用 $fetch）', () => {
    expect(settings).toMatch(/import \{ useMediaUploadCover \} from '~~\/composables\/useMedia'/)
    expect(settings).toContain('await useMediaUploadCover(file)')
    expect(settings).not.toContain('$fetch(')
  })

  it('cover_image 随 PUT /users/me 一起提交，清空写 null', () => {
    expect(settings).toMatch(/await apiFetch\(\s*'\/users\/me'/)
    expect(settings).toContain('cover_image: profile.cover_image || null')
  })

  it('回显与本地态同源于 store 的 cover_image，保存后不会出现表单跳值', () => {
    expect(settings).toMatch(/profile\.cover_image = String\(u\.cover_image \?\? ''\)/)
  })

  it('文件输入框带 accept 与 label 关联，上传中禁用按钮', () => {
    expect(settings).toContain('accept="image/*"')
    expect(settings).toMatch(/<Label for="profile-cover"/)
    expect(settings).toContain(':disabled="savingProfile || coverUploading"')
  })
})

describe('封面展示位', () => {
  it.each([
    ['个人中心 pages/account/index.vue', account],
    ['作者主页 pages/authors/[username].vue', author]
  ])('%s 仅在有封面时渲染 <img>，且按装饰图处理', (_name, src) => {
    expect(src).toMatch(/v-if="coverImage"/)
    expect(src).toMatch(/<img[\s\S]{0,120}:src="coverImage"/)
    expect(src).toMatch(/<img[\s\S]{0,200}alt=""/)
  })

  it('作者主页的 cover_image 在响应类型里声明（漏了只会静默不显，不会报错）', () => {
    expect(author).toContain('cover_image?: string | null')
  })
})

describe('四语文案', () => {
  it('account 封面键在四种语言下齐全且非空', () => {
    const keys = ['fieldCover', 'fieldCoverHint', 'coverUpload', 'coverReplace', 'coverRemove']
    for (const data of locales) {
      const section = data.account ?? {}
      for (const key of keys) {
        expect(section[key], `${key} 缺失`).toBeTruthy()
      }
    }
  })
})
