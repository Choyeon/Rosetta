/**
 * 收藏（/api/favorites*）落地契约（静态源码断言，不开浏览器）。
 *
 * 后端这一族 12 个端点自上线起就绪、前端零消费（见 frontend/docs/API_COVERAGE.md 的
 * favorite 行）。本批次把它接成两处界面：文章详情页的收藏钮 + 个人中心「我的收藏」档位
 * （收藏夹筛选、移动、备注、取消、收藏夹管理）。路径/动词写死在字符串字面量里，
 * 写错的实测表现是 405/404 而不是编译错误，所以这里把口径钉住：
 * 1. useFavorites 是这一族的唯一出口，且只暴露真的有消费点的方法
 *    （曾经 return 一个未定义的 getFavorites —— 运行时 undefined is not a function，
 *     TS 也可能因索引签名放过；现在按导出名逐个核对）；
 * 2. 列表档位必须复用 /account 同一条响应式 useAPI 链（url/key 随档位变），
 *    不能在页面里另造一套裸 $fetch；
 * 3. 取消收藏走 by-post（DELETE /favorites/post/{id}）而不是按行 ID——
 *    表上没有 (user_id, post_id) 唯一约束，按行删会让重复行留在列表里；
 * 4. 收藏钮先 check 再决定 POST/DELETE：POST /favorites 对重复收藏回 400，不是 toggle；
 * 5. 详情/收藏状态是私有态，SSR 首字节不得出现（初值 false + 只在客户端发 check）；
 * 6. 收藏夹列表里的 post.title 是后端 Post.title 的 JSON 原值（这一族不按 lang 解析），
 *    渲染必须过 resolveLocalized，否则界面打出 [object Object]；
 * 7. 四语键补齐。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const read = (p: string) => readFileSync(resolve(ROOT, p), 'utf-8')

const favorites = read('composables/useFavorites.ts')
const account = read('pages/account/index.vue')
const detail = read('pages/posts/[slug].vue')
const comments = read('composables/useComments.ts')

/** 四语共有键：account.* 与 favorites.* 两段。 */
const ACCOUNT_KEYS = [
  'tabFavorites', 'emptyFavorites', 'folderAll', 'folderNone', 'moveFolder',
  'editNote', 'unfavorite', 'unfavorited', 'moved', 'noteTitle', 'noteHint',
  'notePlaceholder', 'noteSaved', 'manageFolders', 'manageFoldersHint',
  'noFolders', 'newFolderPlaceholder', 'addFolder', 'folderCreated',
  'folderRenamed', 'folderDeleted'
]
const FAVORITES_KEYS = ['add', 'favorited', 'added', 'removed', 'loginRequired']

describe('composables/useFavorites.ts 是收藏族的唯一出口', () => {
  it.each([
    ['GET 列表', 'useAPI<FavoriteFolderList>(\'/favorites/folders\''],
    ['POST check', 'apiFetch<FavoriteCheckResult>(\'/favorites/check\''],
    ['POST 收藏', 'apiFetch<FavoriteActionResponse>(\'/favorites\''],
    ['DELETE 按文章取消', '`/favorites/post/${postId}`, { method: \'DELETE\' }'],
    ['PATCH 按文章移夹', '`/favorites/post/${postId}/folder`'],
    ['PATCH 按文章改备注', '`/favorites/post/${postId}/note`'],
    ['POST 建收藏夹', 'apiFetch<FavoriteActionResponse>(\'/favorites/folders\''],
    ['PUT 改收藏夹', '`/favorites/folders/${folderId}`'],
    ['DELETE 删收藏夹', '`/favorites/folders/${folderId}`, { method: \'DELETE\' }']
  ])('%s 走与后端一致的字面量：%s', (_name, literal) => {
    expect(favorites).toContain(literal)
  })

  it('不裸用 $fetch，也不按行 ID 操作收藏（by-row 变体刻意不包装）', () => {
    expect(favorites).not.toMatch(/\$fetch\(/)
    expect(favorites).not.toMatch(/apiFetch<[^>]*>\(\s*[`'"]\/favorites\/\$\{/)
  })

  it('导出的每个方法都在文件里真的定义（曾经 return 过未定义的 getFavorites）', () => {
    const block = favorites.slice(favorites.lastIndexOf('  return {'))
    const exported = [...block.matchAll(/^\s{4}(\w+),$/gm)].map(m => m[1])
    expect(exported.length).toBeGreaterThan(0)
    for (const name of exported) {
      expect(favorites, `useFavorites 返回了未定义的 ${name}`)
        .toContain(`const ${name} = `)
    }
  })
})

describe('个人中心「我的收藏」档位', () => {
  it('档位枚举含 favorites，且列表沿用同一条响应式 useAPI 链', () => {
    expect(account).toContain(`type AccountTab = 'posts' | 'comments' | 'likes' | 'favorites' | 'history'`)
    expect(account).toContain(`tab.value === 'favorites' ? '/favorites' : \`/blog/users/me/\${tab.value}\``)
    expect(account).toContain('useAPI<AccountList>(() => listUrl.value')
    expect(account).not.toMatch(/\$fetch\(/)
  })

  it('收藏夹筛选写在 query.folder，且切夹时复位分页', () => {
    expect(account).toContain('folder_id: folderFilter.value ?? undefined')
    expect(account).toContain('delete merged.folder')
    expect(account).toContain('delete merged.page')
  })

  it('取消收藏走 by-post，备注清空写 null（不是空串）', () => {
    expect(account).toContain('favoritesAPI.removeFavoriteByPost(postId)')
    expect(account).toContain('noteDraft.value.trim() || null')
  })

  it('收藏行的文章标题过 resolveLocalized（后端这一族回的是 JSON 原值）', () => {
    expect(account).toContain('resolveLocalized(row.post.title)')
  })
})

describe('文章详情页收藏钮', () => {
  it('先 check 再决定动词，不在未登录时发请求', () => {
    expect(detail).toContain('favoritesAPI.checkFavorites([Number(pid)]')
    expect(detail).toContain('if (favorited.value) {')
    expect(detail).toContain('favoritesAPI.addFavorite(pid)')
    expect(detail).toContain('favoritesAPI.removeFavoriteByPost(pid)')
    expect(detail).toContain('if (!import.meta.client || !pid || !authStore.accessToken) return')
  })

  it('私有态初值为 false：SSR 首字节不出现「已收藏」', () => {
    expect(detail).toContain('const favorited = ref<boolean>(false)')
  })

  it('图标取自 SSR 安全的 lucide-svg-icons（本页是 SSR 页，不得 import @lucide/vue）', () => {
    expect(detail).toMatch(/import \{[\s\S]*?Bookmark[\s\S]*?\} from '~~\/lib\/lucide-svg-icons'/)
    expect(detail).not.toContain('@lucide/vue')
  })
})

describe('评论反应的取消口', () => {
  it('emoji 在路径上（DELETE /comments/{id}/reactions/{emoji}），不放 body', () => {
    expect(comments).toContain('`/comments/${id}/reactions/${encodeURIComponent(emoji)}`')
  })
})

describe('四语文案', () => {
  it.each(['zh', 'en', 'ja', 'zh_Hant'] as const)('%s 具备收藏相关键', (locale) => {
    const messages = JSON.parse(
      readFileSync(resolve(ROOT, `i18n/locales/${locale}.json`), 'utf-8')
    ) as Record<string, Record<string, string>>
    for (const key of ACCOUNT_KEYS) {
      expect(messages.account?.[key], `${locale} 缺 account.${key}`).toBeTruthy()
    }
    for (const key of FAVORITES_KEYS) {
      expect(messages.favorites?.[key], `${locale} 缺 favorites.${key}`).toBeTruthy()
    }
  })
})
