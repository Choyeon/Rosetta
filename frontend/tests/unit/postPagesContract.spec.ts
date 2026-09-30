/**
 * 文章列表 / 编辑页的跨端契约（源码静态扫描，不挂载组件）。
 *
 * 仓库的"页面测试"一律是这种形态：Vue 模板里的字符串拼错不会报错也不会警告，只会静默
 * 失效，类型检查和运行时都抓不到。这里钉的是"端点是否真被调"、"字段语义是否与后端一致"
 * 这类契约。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), 'utf8')

const publicList = read('pages/posts/index.vue')
const adminList = read('pages/admin/content/posts/index.vue')
const postForm = read('components/admin/PostForm.vue')
// vitest 的 cwd 是仓库根（不是 frontend/），后端源码要往回一层
const blogApi = read('../backend/api/blog.py')

describe('公开文章列表页', () => {
  it('筛选状态同步进 URL（否则刷新/分享/后退全部丢失）', () => {
    expect(publicList).toMatch(/router\.replace\(\{ query:/)
  })

  it('初始状态从 URL 读，且 sort 只接受白名单值', () => {
    expect(publicList).toMatch(/route\.query\.page/)
    expect(publicList).toMatch(/route\.query\.category/)
    expect(publicList).toMatch(/route\.query\.sort === 'popular' \? 'popular' : 'latest'/)
  })

  it('canonical 与 URL 同步函数同源（不能声明一个不存在的规范地址）', () => {
    // 都读 canonicalQuery，避免两处各写一份查询串慢慢漂开
    expect(publicList).toMatch(/const canonicalQuery = computed/)
    const canonicalIdx = publicList.indexOf('const canonical = computed')
    const syncIdx = publicList.indexOf('function syncUrl')
    expect(canonicalIdx).toBeGreaterThan(-1)
    expect(syncIdx).toBeGreaterThan(-1)
    expect(publicList.slice(canonicalIdx)).toMatch(/canonicalQuery\.value/)
    expect(publicList.slice(syncIdx)).toMatch(/canonicalQuery\.value/)
  })

  it('翻页/换筛选时有进行中状态（旧数据仍在，不能只靠骨架屏）', () => {
    expect(publicList).toMatch(/const busy = computed\(\(\) => pending\.value\)/)
    expect(publicList).toMatch(/:aria-busy="busy"/)
  })

  it('空态区分"筛选无结果"与"真的一篇都没有"', () => {
    expect(publicList).toMatch(/hasActiveFilter \? t\('posts\.noMatch'\)/)
    expect(publicList).toMatch(/hasActiveFilter \? t\('posts\.noMatchDesc'\)/)
    expect(publicList).toMatch(/clearFilters = \(\)/)
    expect(publicList).toMatch(/@click="clearFilters"/)
  })

  it('排序参数只在非默认时才发送', () => {
    expect(publicList).toMatch(/sort: sortBy\.value === 'popular' \? 'popular' : undefined/)
  })

  it('不再每次搜索都顺手刷新分类列表', () => {
    expect(publicList).not.toMatch(/refreshCategories\(\)/)
  })
})

describe('后台文章管理列表页', () => {
  it('翻页与换筛选必须清空选中项（跨页残留会误删看不见的文章）', () => {
    expect(adminList).toMatch(/function reload\(\)[\s\S]*?selectedIds\.value = \[\]/)
  })

  it('所有重载都走 scheduleLoad，不存在"置 page=1 又手动 loadPosts"的双请求写法', () => {
    // 契约：page 的 watch 是 pre-flush，直接再调一次 loadPosts 会发出两条相同请求
    expect(adminList).toMatch(/function scheduleLoad\(\)/)
    expect(adminList).toMatch(/watch\(\[page, pageSize\], \(\) => \{\s*scheduleLoad\(\)\s*\}\)/)
    const reloadBody = adminList.match(/function reload\(\)[\s\S]*?\n}/)?.[0] ?? ''
    expect(reloadBody).toMatch(/scheduleLoad\(\)/)
    expect(reloadBody).not.toMatch(/loadPosts\(\)/)
  })

  it('请求失败不再静默吞掉，给出重试入口', () => {
    expect(adminList).toMatch(/const loadError = ref<string \| null>\(null\)/)
    expect(adminList).toMatch(/loadError\.value = e instanceof Error/)
    expect(adminList).toMatch(/v-if="loadError"/)
  })

  it('分类筛选只传 slug（后端 Category.slug == category，传 id 永远匹配不上）', () => {
    expect(adminList).toMatch(/:value="c\.slug"/)
    expect(adminList).not.toMatch(/c\.slug \|\| c\.id\.toString\(\)/)
  })

  it('列表展示"最后更新"，且该字段在前端类型里存在', () => {
    expect(adminList).toMatch(/\{ key: 'updated_at', title: '最后更新'/)
    expect(adminList).toMatch(/#cell-updated_at/)
    expect(read('composables/useAdminManage.ts')).toMatch(/updated_at\?: string \| null/)
  })

  it('状态与日期筛选与分类保持一致：选完即生效', () => {
    expect(adminList).toMatch(/watch\(\[statusFilter, createdStart, createdEnd\]/)
  })
})

describe('文章编辑表单', () => {
  it('定时时间走本地墙钟换算，不再 slice(0,16)', () => {
    expect(postForm).toMatch(/from '~~\/lib\/datetime'/)
    expect(postForm).toMatch(/form\.scheduled_at = toDateTimeLocal\(data\.scheduled_at\)/)
    expect(postForm).toMatch(/payload\.scheduled_at = fromDateTimeLocal\(form\.scheduled_at\)/)
    expect(postForm).not.toMatch(/scheduled_at\.slice\(0, 16\)/)
  })

  it('要能清掉的字段显式发送空值（undefined 会被 JSON 丢弃 → exclude_unset 视作未改动）', () => {
    expect(postForm).toMatch(/category_id: form\.category_id \?\? null/)
    expect(postForm).toMatch(/cover_image: form\.cover_image \?\? ''/)
    expect(postForm).not.toMatch(/category_id: form\.category_id \|\| undefined/)
  })

  it('slug 源不再只盯 zh 标题', () => {
    expect(postForm).toMatch(/from '~~\/lib\/postEditor'/)
    expect(postForm).toMatch(/const slugSource = computed\(\(\) => slugSourceTitle\(form\.title\)\)/)
    expect(postForm).not.toMatch(/watch\(\s*\(\) => form\.title\.zh/)
  })

  it('定时时间必须在提交前校验不晚于现在', () => {
    expect(postForm).toMatch(/const schedErr = scheduledError\.value/)
  })

  it('给出字数/阅读时长与未保存状态', () => {
    expect(postForm).toMatch(/contentStats\.words/)
    expect(postForm).toMatch(/v-if="isDirty"/)
  })
})

describe('后端文章列表接口', () => {
  it('时间排序用 coalesce 兜住 NULL（草稿不能沉底）', () => {
    expect(blogApi).toMatch(/func\.coalesce\(Post\.published_at, Post\.created_at\)\.desc\(\)/)
  })

  it('排序带唯一键做 tiebreaker（保证分页稳定）', () => {
    expect(blogApi).toMatch(/Post\.id\.desc\(\)/)
  })

  it('sort 进入缓存键', () => {
    expect(blogApi).toMatch(/f"so\{sort\}"/)
  })

  it('未知 sort 回退 latest 而不是 422', () => {
    expect(blogApi).toMatch(/def _normalize_list_sort/)
    expect(blogApi).toMatch(/return LIST_SORT_LATEST/)
  })
})
