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
const postDetail = read('pages/posts/[slug].vue')
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

  it('canonical 由 useSeo 单源产出，页面只保留地址栏同步用的查询串', () => {
    // 旧口径是页面自己拼一份 canonical：与 useSeo 的那条并存 → <head> 里两条规范地址，
    // 且地址取自请求 Host（swr 缓存会把 Host 固化给所有访客）。
    expect(publicList).toMatch(/const canonicalQuery = computed/)
    expect(publicList).toMatch(/function syncUrl/)
    expect(publicList).toMatch(/syncUrl[\s\S]{0,200}canonicalQuery\.value/)
    expect(publicList).not.toMatch(/const canonical = computed/)
    expect(publicList).not.toMatch(/rel: 'canonical'/)
    expect(publicList).toMatch(/useSeo\(\{[\s\S]{0,200}?\}\)/)
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

/**
 * 文章编辑流程的收敛契约：草稿不踢出编辑器、slug 冲突不静默改名、系列能读回来。
 *
 * 这三条都属"接口回 200、用户看不出来"的一类：只有真去存一次草稿 / 撞一次名 /
 * 改一次标题才知道，所以钉成静态扫描。
 */
describe('文章编辑流程收敛', () => {
  const newPage = read('pages/admin/content/posts/new.vue')
  const editPage = read('pages/admin/content/posts/[id]/edit.vue')
  const editSchema = read('../backend/schemas/__init__.py')

  it('新建页存完草稿换成编辑态地址（留在 /new 会让下一次保存再 POST 一篇）', () => {
    expect(postForm).toMatch(/const settleAfterSave = /)
    expect(newPage).toMatch(/router\.replace\(`\/admin\/content\/posts\/\$\{saved\.id\}\/edit`\)/)
  })

  it('编辑页存草稿留在原页继续写，只有发布/定时才跳列表', () => {
    expect(editPage).toMatch(/status === 'draft'\) return/)
    // 留在原页时 submitted 必须保持 false：置真会一并关掉离开确认、beforeunload
    // 与卸载时写本地草稿，之后所有改动都变成"静默丢稿"
    expect(postForm).toMatch(/if \(props\.mode === 'edit' && status === 'draft'\)/)
    expect(postForm).toMatch(/initialStateSnapshot\.value = JSON\.stringify\(form\)\n\s*try \{/)
  })

  it('系列与章节序号显式提交，且编辑端点会读回来', () => {
    expect(postForm).toMatch(/series_id: form\.series_id \?\? null,/)
    expect(postForm).toMatch(/series_order: form\.series_order \|\| 0,/)
    expect(postForm).toMatch(/form\.series_id = data\.series_id \?\? null/)
    expect(editSchema).toMatch(/series_id=post\.series_id,/)
    expect(editSchema).toMatch(/series_order=post\.series_order,/)
  })

  it('slug 冲突改成明确拒绝，不再加时间戳后缀把冲突藏起来', () => {
    expect(blogApi).not.toMatch(/strftime\('%Y%m%d%H%M%S'\)/)
    expect(blogApi).toMatch(/该 slug 已被其它文章占用/)
    // PUT 路径也要挡：Post.slug 有唯一约束，不挡就是 IntegrityError → 500
    expect(blogApi).toMatch(/Post\.slug == new_slug, Post\.id != post\.id/)
  })

  it('未发布文章点预览先说明前台会 404（预览读的是库里已保存的那一篇）', () => {
    expect(postForm).toMatch(/if \(form\.status !== 'published'\)/)
  })

  it('分类/标签色点的缺省色走主题令牌，不写死十六进制', () => {
    expect(postForm).not.toMatch(/#94a3b8/)
    expect(postForm).toMatch(/:class="c\.color \? '' : 'bg-muted-foreground\/40'/)
  })
})

/**
 * 密码保护文章的详情页闸门。
 *
 * 这条链路曾有三个各自独立、且都只在运行时才暴露的缺陷（生产表现：点进加密文章
 * 整页空白）：闸门状态用 watch+ref 维护（SSR 期 watch 的 immediate 回调拿到的是
 * null，正文与闸门判定分家）、正文容器用 v-if 隐藏（SSR 与 hydration 的节点树
 * 不一致）、解锁走会吞掉 401 的口子（用户被判成"登录过期"）。模板与状态机
 * 拼错都不报错，只有真实浏览器里才看得见，所以钉成静态契约。
 */
describe('密码保护文章详情页闸门', () => {
  it('闸门与提示走 computed，且与正文同源', () => {
    expect(postDetail).toMatch(/const needPassword = computed\(/)
    // 允许带泛型实参：postEncryptionHint 实际写成 computed<string | null>(…)
    expect(postDetail).toMatch(/const postEncryptionHint = computed(<[^>]*>)?\(/)
    // 判据必须同时看后端的 is_password_protected 与"正文是否为空"：
    // 只看前者会在已解锁的会话里再次锁上，只看后者会把普通空正文判成加密。
    expect(postDetail).toMatch(/is_password_protected[\s\S]{0,120}!\s*content/)
  })

  it('闸门未打开时不渲染正文，也不去拉投票（投票卡会出现在密码框上方）', () => {
    // 闸门与正文在模板里必须是同一个 needPassword：两个分支若各自判一次，
    // "闸门说锁着、正文说开着"就会渲染出一片空白。
    const gateAt = postDetail.indexOf('<div v-if="needPassword">')
    const bodyAt = postDetail.indexOf('<div v-show="!needPassword">')
    expect(gateAt, '闸门分支没走 needPassword').toBeGreaterThan(-1)
    // 正文容器必须是 v-show：v-if 让 SSR 与 hydration 的节点数不同，
    // 表现为整页 hydration 警告 + 空白。
    expect(bodyAt, '正文容器没用 v-show 隐藏').toBeGreaterThan(gateAt)
    expect(postDetail).not.toMatch(/<div v-if="!needPassword">/)
    // 拉投票必须先过闸门：needPassword 为真时给 null（并入 Promise.all 也不发请求），
    // 防止 poll 内容出现在密码框上方；解锁后的补拉见 watch(needPassword)。
    const pollsAt = postDetail.indexOf('needPassword.value ? null : pollsAPI.fetchActivePolls')
    expect(pollsAt, '拉投票前没有闸门判定').toBeGreaterThan(bodyAt)
  })

  it('密码经 X-Post-Password 头随 GET 发送，不进查询串', () => {
    // 查询串会被 nginx access log 明文落盘，长正文/长密码还会撞 414。
    expect(postDetail).toMatch(/'X-Post-Password': articleStoredPwd\.value/)
    expect(postDetail).toMatch(/headers\['X-Post-Password'\] = articleStoredPwd\.value/)
    expect(postDetail).not.toMatch(/query:\s*\{[^}]*password/i)
  })

  it('解锁失败只回到错误态，不清登录态也不跳登录页', () => {
    expect(postDetail).toMatch(/articlePwdError\.value = true/)
    expect(postDetail).not.toMatch(/authStore\.logout|navigateTo\('\/login/)
  })
})
