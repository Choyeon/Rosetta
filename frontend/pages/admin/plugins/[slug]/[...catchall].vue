<script setup lang="ts">
/**
 * 插件后台承载页：统一接管 /admin/plugins/<slug>/**
 *
 * 设计策略（最小实现，避免与现有 Admin 功能冲突）：
 *
 *  1) 若插件提供 admin_route_prefix + 具体后端路径：用 <iframe> 将该路径渲染为
 *     一个自洽的插件页面（插件可返回独立 HTML，或与现有 useAPI 交互的 JSON）。
 *     由于 FastAPI 路由挂载到 /api/admin/plugins/{slug}，这里 iframe 的默认值
 *     为 `/api/admin/plugins/{slug}/<catchall>`（保证后端返回的 HTML 能正常加载）。
 *
 *  2) 若 catchall 为空 → 退回「插件信息卡片」占位，显示 slug + 返回按钮。
 *
 *  3) 样式与其它后台页面保持一致（沿用 Card / Button / shadcn 风格）。
 */
import { ArrowLeft, Puzzle, ExternalLink, AlertTriangle } from '@lucide/vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'

definePageMeta({
  ssr: false,
  layout: 'admin'
})

const route = useRoute()

const slug = computed(() => {
  const v = route.params.slug
  return Array.isArray(v) ? v[0] : String(v ?? '')
})

const catchallSegments = computed<string[]>(() => {
  const raw = (route.params as { catchall?: string | string[] }).catchall
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string' && raw.length) return [raw]
  return []
})

const catchallPath = computed(() => catchallSegments.value.map(encodeURIComponent).join('/'))

// iframe src：代理到插件的 FastAPI 路由前缀（带所有剩余 path segment 透传）
// 例：slug=guestbook-rss, catchall=[settings] => /api/admin/plugins/guestbook-rss/settings
const iframeSrc = computed(() => {
  if (!slug.value) return ''
  const base = `/api/admin/plugins/${slug.value}`
  return catchallPath.value ? `${base}/${catchallPath.value}` : base
})

const iframeReady = ref(false)
const iframeLoadFailed = ref(false)
const iframeHeight = ref('72vh')

function onIframeLoad() {
  iframeReady.value = true
  iframeLoadFailed.value = false
}
function onIframeError() {
  iframeLoadFailed.value = true
  iframeReady.value = false
}

const goBack = () => navigateTo('/admin/system/plugins', { replace: false })
const openInNewTab = () => iframeSrc.value && window.open(iframeSrc.value, '_blank', 'noopener,noreferrer')
</script>

<template>
  <div class="plugin-host-page space-y-4">
    <!-- 顶部条：插件 slug / 返回按钮 / 新标签打开 -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3 min-w-0">
        <Button
          size="sm"
          variant="ghost"
          class="shrink-0"
          @click="goBack"
        >
          <ArrowLeft class="size-4 mr-1.5" />
          返回插件管理
        </Button>
        <div class="min-w-0">
          <h1 class="text-xl md:text-2xl font-semibold tracking-tight flex items-center gap-2 min-w-0">
            <Puzzle class="shrink-0 size-6 text-primary" />
            <span class="truncate">{{ slug || '未知插件' }}</span>
            <Badge
              v-if="slug"
              variant="outline"
              class="shrink-0 font-mono text-[11px]"
            >
              {{ catchallPath || '/' }}
            </Badge>
          </h1>
          <p class="text-sm text-muted-foreground mt-0.5 truncate">
            插件独立后台承载页 · 页面来源：
            <code class="px-1.5 py-0.5 rounded bg-muted/70 text-[11.5px] font-mono">
              {{ iframeSrc || '(空)' }}
            </code>
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          :disabled="!iframeSrc"
          @click="openInNewTab"
        >
          <ExternalLink class="size-4 mr-1.5" />
          新标签打开
        </Button>
      </div>
    </div>

    <!-- 无 catchall：占位信息卡 -->
    <Card
      v-if="!catchallPath"
      class="overflow-hidden"
    >
      <CardHeader>
        <CardTitle class="flex items-center gap-2 text-lg">
          <Puzzle class="size-5 text-primary" />
          插件承载页占位
        </CardTitle>
        <CardDescription>
          当前未指定具体子路径。插件在 manifest.admin_menu.path 或其前端页面链接中应包含
          具体子段（例如 <code class="px-1 rounded bg-muted">/admin/plugins/{slug}/settings</code>）。
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-3 text-sm">
        <Alert variant="default">
          <AlertTriangle class="size-4" />
          <AlertTitle>路径提示</AlertTitle>
          <AlertDescription>
            如果插件未提供可渲染的 HTML 端点，这里将展示为空。插件可通过
            <code class="px-1 rounded bg-muted">ctx.register_admin_router()</code>
            注册 FastAPI 路由，并在该路由返回 HTML / JSON / 下载文件等任意响应。
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>

    <!-- 有 catchall：iframe 承载 -->
    <Card
      v-else
      class="overflow-hidden"
    >
      <CardHeader class="pb-2">
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <div class="space-y-1">
            <CardTitle class="text-base">
              <span class="opacity-70 mr-2">插件路由:</span>
              <span class="font-mono text-sm">{{ iframeSrc }}</span>
            </CardTitle>
            <CardDescription>
              若插件接口返回 JSON 或 401/404，下方会显示错误提示或浏览器默认渲染。
            </CardDescription>
          </div>
          <div class="flex items-center gap-2">
            <Badge
              v-if="iframeReady"
              variant="secondary"
            >
              已加载
            </Badge>
            <Badge
              v-else-if="iframeLoadFailed"
              variant="destructive"
            >
              加载失败
            </Badge>
            <Badge
              v-else
              variant="outline"
            >
              加载中…
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent class="p-0">
        <div class="relative w-full border-t border-border bg-muted/20">
          <div
            v-if="!iframeReady && !iframeLoadFailed"
            class="absolute inset-0 p-4 space-y-3 pointer-events-none"
          >
            <Skeleton class="h-6 w-1/3" />
            <Skeleton class="h-3 w-2/3" />
            <Skeleton class="h-40 w-full" />
            <Skeleton class="h-20 w-1/2" />
          </div>
          <iframe
            :src="iframeSrc"
            :style="{ height: iframeHeight }"
            class="w-full block bg-background border-0 plugin-host-frame"
            referrerpolicy="no-referrer-when-downgrade"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
            title="插件后台承载页"
            @load="onIframeLoad"
            @error="onIframeError"
          />
        </div>
        <Alert
          v-if="iframeLoadFailed"
          variant="destructive"
          class="mx-4 my-4"
        >
          <AlertTriangle class="size-4" />
          <AlertTitle>承载页加载失败</AlertTitle>
          <AlertDescription>
            插件路由 <code class="px-1 rounded bg-muted">{{ iframeSrc }}</code>
            未能正常返回内容。请确认：
            <ol class="list-decimal list-inside mt-1.5 space-y-0.5 pl-1">
              <li>插件已激活并成功调用了 <code>ctx.register_admin_router()</code>。</li>
              <li>对应 GET 路由存在且返回 2xx（可在新标签打开查看具体响应）。</li>
              <li>若该路由需要特殊参数，更新菜单的 <code>path</code> 或前端链接。</li>
            </ol>
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.plugin-host-frame {
  min-height: 60vh;
}
</style>
