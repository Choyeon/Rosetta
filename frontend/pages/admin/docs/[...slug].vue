<script setup lang="ts">
/**
 * Rosetta 后台开发文档浏览器。
 *
 * 路由：/admin/docs/:slug* ；slug 为空或缺失时回退到 index。
 * 渲染流程：
 *   1) 后端 GET /api/docs/{slug} 读取磁盘 Markdown 原文 + 标题
 *   2) 前端使用 marked 解析为 HTML；尽量用 marked-highlight + highlight.js
 *      对代码块做语法高亮，任意依赖加载失败则退化为「纯 marked 渲染」。
 *   3) 左侧目录通过 GET /api/docs/list 拉取，带内存缓存。
 */

import { fetchDocsCatalog, fetchDocsDoc, groupByCategory, type DocsCatalogItem } from '~~/composables/useDocsCatalog'
import { Skeleton } from '~~/components/ui/skeleton'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { useDocsCatalog as useCatalogExport } from '~~/composables/useDocsCatalog'

// 后台布局内渲染：带侧边栏/面包屑，可随时跳转其他 Admin 页面
definePageMeta({
  ssr: false,
  layout: 'admin'
})

// 重新导出给 Vue 模板：
const _ = useCatalogExport

const route = useRoute()

/** 当前文档元信息（用于页面头标题/副标题，目录未加载完时给兜底值） */
const currentDocMeta = computed<DocsCatalogItem | undefined>(() =>
  catalogState.value.items.find(it => it.slug === slug.value)
)
const displayTitle = computed(() =>
  currentDocMeta.value?.title
  || (slug.value === 'index' ? '开发文档首页' : docState.value.title)
  || '开发文档'
)

const slug = computed<string>(() => {
  const raw = route.params.slug
  if (Array.isArray(raw)) {
    if (raw.length === 0) return 'index'
    const first = raw[0]
    return typeof first === 'string' && first.trim() ? first : 'index'
  }
  if (typeof raw === 'string' && raw.trim()) return raw
  return 'index'
})

const catalogState = ref<{
  loading: boolean
  items: DocsCatalogItem[]
  grouped: ReturnType<typeof groupByCategory>
}>({
  loading: true,
  items: [],
  grouped: []
})

const docState = ref<{
  loading: boolean
  title: string
  html: string
  error: string | null
}>({
  loading: true,
  title: '',
  html: '',
  error: null
})

// ═══════════════════════════════════════════════════════════════════════
// Markdown 渲染（marked + marked-highlight + highlight.js 降级链）
// ═══════════════════════════════════════════════════════════════════════

let _rendererReady: Promise<(md: string) => string> | null = null

async function _buildRenderer(): Promise<(md: string) => string> {
  // 1. 加载 marked 基础
  const markedMod = await import('marked')
  const { Marked } = markedMod

  // 2. 尝试加载 marked-highlight + highlight.js；失败则回退到无高亮渲染
  try {
    const markedHlMod = await import('marked-highlight')
    const hlMod = await import('highlight.js')
    const { markedHighlight } = markedHlMod
    const hl = hlMod.default ?? hlMod

    const marked = new Marked(
      markedHighlight({
        langPrefix: 'hljs language-',
        highlight(code, lang) {
          try {
            const language = lang && hl.getLanguage(lang) ? lang : 'plaintext'
            return hl.highlight(code, { language, ignoreIllegals: true }).value
          } catch {
            return code
          }
        }
      })
    )
    marked.setOptions({
      gfm: true,
      breaks: false
    })
    return (md: string) => marked.parse(md) as string
  } catch {
    // 高亮依赖不可用：纯 marked 渲染，无代码块高亮
    const marked = new Marked()
    marked.setOptions({
      gfm: true,
      breaks: false
    })
    return (md: string) => marked.parse(md) as string
  }
}

async function renderMarkdown(md: string): Promise<string> {
  if (!_rendererReady) _rendererReady = _buildRenderer()
  const renderer = await _rendererReady
  return renderer(md)
}

// ═══════════════════════════════════════════════════════════════════════
// 数据加载
// ═══════════════════════════════════════════════════════════════════════

async function loadCatalog() {
  catalogState.value.loading = true
  try {
    const data = await fetchDocsCatalog()
    catalogState.value.items = data.items
    catalogState.value.grouped = groupByCategory(data.items)
  } catch (err) {
    console.error('[docs] 加载目录失败', err)
  } finally {
    catalogState.value.loading = false
  }
}

async function loadDoc() {
  docState.value.loading = true
  docState.value.error = null
  try {
    const doc = await fetchDocsDoc(slug.value, false)
    docState.value.title = doc.title
    docState.value.html = await renderMarkdown(doc.markdown)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    docState.value.error = msg
    docState.value.title = '加载失败'
    docState.value.html = `<div class="text-sm text-muted-foreground">
      无法加载文档：<code>${msg}</code>。请确认后端 <code>/api/docs/${slug.value}</code> 可用。
    </div>`
  } finally {
    docState.value.loading = false
  }
}

async function go(s: string) {
  if (s === slug.value) return
  await navigateTo(`/admin/docs/${s === 'index' ? 'index' : s}`)
}

// 首屏：目录优先（侧栏先出），文档并行
onMounted(async () => {
  // 预加载 highlight.js 样式（客户端）
  try {
    await import('highlight.js/styles/github.css')
  } catch {
    /* 不支持 css 导入时使用内联样式（见下方 scoped）兜底 */
  }
  await Promise.all([loadCatalog(), loadDoc()])
})

// slug 切换：只刷新文档；页面滚动模式下需手动回到顶部
watch(slug, () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
  loadDoc().catch(() => { /* 错误已写入 docState.error */ })
})
</script>

<template>
  <div class="docs-shell flex flex-col gap-4 lg:gap-5 lg:flex-row lg:items-start">
    <!-- 侧边栏：文档目录（页面滚动时吸顶，目录过长时卡片内部滚动） -->
    <aside class="shrink-0 w-full lg:w-[260px] xl:w-[280px] lg:sticky lg:top-4 lg:max-h-[calc(100dvh-6.5rem)]">
      <div class="rounded-xl border border-border/80 bg-card/60 backdrop-blur-md text-card-foreground shadow-soft/60 flex flex-col max-h-full lg:h-full overflow-hidden">
        <div class="flex items-center gap-2 px-4 py-3 border-b shrink-0">
          <span class="font-semibold text-sm">开发文档</span>
          <span class="text-[11px] text-muted-foreground">zh-CN</span>
        </div>
        <ScrollArea class="max-h-[320px] lg:flex-1 lg:min-h-0 lg:max-h-none">
          <div
            v-if="catalogState.loading"
            class="flex flex-col gap-2 p-3"
          >
            <Skeleton
              v-for="i in 6"
              :key="i"
              class="h-7 rounded-md"
            />
          </div>
          <div
            v-else
            class="p-2"
          >
            <template
              v-for="g in catalogState.grouped"
              :key="g.category"
            >
              <div class="px-2 pt-3 pb-1 text-[11px] uppercase tracking-[0.12em] font-semibold text-muted-foreground/80">
                {{ g.category }}
              </div>
              <ul class="flex flex-col gap-0.5 pb-1">
                <li
                  v-for="it in g.items"
                  :key="it.slug"
                >
                  <button
                    type="button"
                    class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors"
                    :class="[
                      slug === it.slug
                        ? 'bg-primary/12 text-primary font-medium'
                        : 'hover:bg-accent hover:text-accent-foreground text-muted-foreground'
                    ]"
                    :disabled="!it.available"
                    @click="go(it.slug)"
                  >
                    <div class="truncate">
                      {{ it.title }}
                    </div>
                    <div
                      v-if="it.description"
                      class="text-[11px] truncate opacity-75 mt-0.5"
                    >
                      {{ it.description }}
                    </div>
                  </button>
                </li>
              </ul>
            </template>
          </div>
        </ScrollArea>
      </div>
    </aside>

    <!-- 正文：随页面整体滚动，不做内部滚动条 -->
    <section class="flex-1 min-w-0">
      <div class="rounded-xl border border-border/80 bg-card text-card-foreground shadow-soft/60">
        <header class="px-5 md:px-8 py-4 border-b flex flex-wrap items-center gap-x-3 gap-y-1">
          <div class="flex items-center gap-2.5 min-w-0">
            <h1 class="text-xl md:text-2xl font-semibold tracking-tight font-display truncate">
              {{ displayTitle }}
            </h1>
            <span
              v-if="currentDocMeta?.category"
              class="shrink-0 text-[11px] px-1.5 py-0.5 rounded-md bg-primary/10 text-primary font-medium"
            >
              {{ currentDocMeta.category }}
            </span>
          </div>
          <p
            v-if="currentDocMeta?.description"
            class="w-full text-xs text-muted-foreground truncate"
          >
            {{ currentDocMeta.description }}
          </p>
        </header>

        <div>
          <div
            v-if="docState.loading"
            class="flex flex-col gap-3 p-5 md:p-8"
          >
            <Skeleton class="h-5 w-4/5 rounded-md" />
            <Skeleton class="h-5 w-11/12 rounded-md" />
            <Skeleton class="h-5 w-2/3 rounded-md" />
            <Skeleton class="h-5 w-3/4 rounded-md" />
            <Skeleton class="h-5 w-5/6 rounded-md" />
            <Skeleton class="h-32 w-full rounded-md mt-4" />
          </div>

          <!-- eslint-disable-next-line vue/no-v-html -->
          <article
            v-else
            class="prose-docs px-5 md:px-8 py-6 md:py-8 max-w-none"
            v-html="docState.html"
          />
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* 通用文档排版：prose-docs 作为类名，避免和项目其他 prose 样式混淆。 */
:deep(.prose-docs) {
  color: hsl(var(--foreground));
  line-height: 1.75;
  font-size: 15px;
}
/* 正文首行 H1 与页面头标题重复，隐藏之 */
:deep(.prose-docs > h1:first-child) {
  display: none;
}
:deep(.prose-docs h1),
:deep(.prose-docs h2),
:deep(.prose-docs h3),
:deep(.prose-docs h4) {
  font-weight: 700;
  letter-spacing: -0.01em;
  scroll-margin-top: 80px;
}
:deep(.prose-docs h1) {
  font-size: 1.9rem;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid hsl(var(--border));
}
:deep(.prose-docs h2) {
  font-size: 1.45rem;
  margin: 2.2rem 0 0.9rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid hsl(var(--border) / 0.75);
}
:deep(.prose-docs h3) {
  font-size: 1.15rem;
  margin: 1.8rem 0 0.6rem;
}
:deep(.prose-docs p) {
  margin: 0.8rem 0;
}
:deep(.prose-docs a) {
  color: hsl(var(--primary));
  text-decoration: underline;
  text-underline-offset: 3px;
}
:deep(.prose-docs a:hover) {
  opacity: 0.85;
}
:deep(.prose-docs ul),
:deep(.prose-docs ol) {
  padding-left: 1.6rem;
  margin: 0.6rem 0 0.6rem 0;
}
:deep(.prose-docs li) {
  margin: 0.2rem 0;
}
:deep(.prose-docs blockquote) {
  margin: 1rem 0;
  padding: 0.5rem 1rem;
  border-left: 4px solid hsl(var(--primary) / 0.6);
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--muted-foreground));
  border-radius: 0 6px 6px 0;
}
:deep(.prose-docs code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.88em;
  background: hsl(var(--muted));
  padding: 0.1em 0.4em;
  border-radius: 5px;
  color: hsl(var(--foreground));
}
:deep(.prose-docs pre) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: #0d1117;
  color: #e6edf3;
  padding: 1rem 1.1rem;
  border-radius: 10px;
  overflow-x: auto;
  margin: 1.1rem 0;
  line-height: 1.6;
  font-size: 13.5px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
}
:deep(.prose-docs pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
  font-size: inherit;
  border-radius: 0;
}
:deep(.prose-docs table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1.2rem 0;
  display: block;
  overflow-x: auto;
  font-size: 14px;
}
:deep(.prose-docs th),
:deep(.prose-docs td) {
  border: 1px solid hsl(var(--border));
  padding: 0.55rem 0.8rem;
  text-align: left;
  vertical-align: top;
}
:deep(.prose-docs th) {
  background: hsl(var(--muted) / 0.55);
  font-weight: 600;
}
:deep(.prose-docs tr:nth-child(even) td) {
  background: hsl(var(--muted) / 0.25);
}
:deep(.prose-docs hr) {
  border: none;
  border-top: 1px solid hsl(var(--border));
  margin: 1.8rem 0;
}
:deep(.prose-docs img) {
  max-width: 100%;
  border-radius: 10px;
}

/* highlight.js 内联兜底样式（在 CSS 导入失败时仍然有可读性） */
:deep(.hljs-comment),
:deep(.hljs-quote) { color: #8b949e; font-style: italic; }
:deep(.hljs-keyword),
:deep(.hljs-selector-tag),
:deep(.hljs-literal),
:deep(.hljs-section),
:deep(.hljs-link) { color: #ff7b72; }
:deep(.hljs-function),
:deep(.hljs-title),
:deep(.hljs-name),
:deep(.hljs-params) { color: #d2a8ff; }
:deep(.hljs-string),
:deep(.hljs-attr),
:deep(.hljs-symbol),
:deep(.hljs-bullet),
:deep(.hljs-addition) { color: #a5d6ff; }
:deep(.hljs-number),
:deep(.hljs-meta),
:deep(.hljs-built_in),
:deep(.hljs-builtin-name),
:deep(.hljs-variable),
:deep(.hljs-template-variable),
:deep(.hljs-type) { color: #79c0ff; }
:deep(.hljs-title.class_),
:deep(.hljs-class) { color: #f0883e; }
</style>
