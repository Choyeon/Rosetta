<!--
  关于页编辑器（SPA / layout=admin）。

  硬契约一：关于页正文的真源只有一个键——站点设置 `basic.about_page_html`。
  前台 pages/about.vue 非空时 sanitizeTrustedAdminHtml 后 v-html、为空时回落内置
  Tabs 模板；本页只 PATCH 这一个键（部分更新，不动 basic 组其余字段），
  并同步从「系统设置 → 基本」里剥离该键（settings.vue 的 GROUP_BLOCK_KEYS），
  「关于页正文」自此只有这一个编辑入口，不再跟站点基础配置混在一张表单里。
  独立页管理器（admin/content/pages）的 exclude_slugs 早就排除了 about，
  这里补的是"编辑入口"这一侧的解耦。

  硬契约二：预览与前台同一条净化链路（lib/sanitize）。不在本页另接 marked——
  about_page_html 的语义就是 HTML，不是 Markdown，编辑器里存什么前台就渲染什么；
  预览能显示、前台不显示的情况只可能来自净化白名单，而两侧用的正是同一份配置。

  硬契约三：清空输入框 → 保存 = 恢复默认模板。恢复不做成"一键直接写库"，
  仍要经过保存按钮，避免点错一下就把自定义正文写没。
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ExternalLink, Eye, Info, Pencil, RotateCcw, Save } from '@lucide/vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Textarea } from '~~/components/ui/textarea'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { fetchSettingsGroup, saveSettingsGroup } from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { sanitizeTrustedAdminHtml } from '~~/lib/sanitize'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()
const { localeHref } = useLocaleLink()
const site = useSite()

const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
/** 已落库的值：脏标记与「恢复上次保存」都以它为基准 */
const saved = ref('')
const draft = ref('')
/** 编辑 / 预览两态；预览用与前台相同的净化链路 */
const mode = ref<'edit' | 'preview'>('edit')

const dirty = computed(() => draft.value !== saved.value)
const hasCustomHtml = computed(() => saved.value.trim().length > 0)
const previewHtml = computed(() => sanitizeTrustedAdminHtml(draft.value))

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await fetchSettingsGroup('basic')
    const html = typeof data.about_page_html === 'string' ? data.about_page_html : ''
    saved.value = html
    draft.value = html
  } catch (e) {
    const err = e as { message?: string }
    loadError.value = err?.message || '加载关于页配置失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await saveSettingsGroup('basic', { about_page_html: draft.value })
    saved.value = draft.value
    toast.success(draft.value.trim() ? '关于页已保存' : '已清空，前台回到默认模板')
    // PATCH 已经清了后端缓存并通知 Nitro 清页面缓存；useSite 的进程内副本要自己刷，
    // 否则当前标签页里的其它读数还是旧的。
    try {
      await site.ensureLoaded({ force: true })
    } catch { /* 刷新失败不改写保存结果 */ }
  } catch {
    // apiFetch 已 toast
  } finally {
    saving.value = false
  }
}

function resetDraft() {
  draft.value = ''
  mode.value = 'edit'
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="关于页"
      description="独立编辑关于页正文；留空即回落到内置模板。内容与独立页管理互不影响。"
      :icon="Info"
    >
      <template #actions>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          as-child
        >
          <NuxtLink
            :to="localeHref('/about')"
            target="_blank"
            rel="noopener"
          >
            <ExternalLink data-icon="inline-start" />
            查看关于页
          </NuxtLink>
        </Button>
        <Button
          size="sm"
          class="rounded-xl"
          :disabled="loading || saving || !dirty"
          @click="save"
        >
          <Save data-icon="inline-start" />
          {{ saving ? '保存中…' : '保存' }}
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="loadError"
      variant="destructive"
    >
      <AlertTitle>加载失败</AlertTitle>
      <AlertDescription class="flex items-center justify-between gap-3">
        <span>{{ loadError }}</span>
        <Button
          variant="outline"
          size="sm"
          @click="load"
        >
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <Card>
      <CardHeader>
        <CardTitle class="flex items-center gap-2 text-base">
          关于页正文
          <Badge :variant="hasCustomHtml ? 'default' : 'secondary'">
            {{ hasCustomHtml ? '自定义内容' : '默认模板' }}
          </Badge>
          <Badge
            v-if="dirty"
            variant="outline"
          >
            未保存
          </Badge>
        </CardTitle>
        <CardDescription>
          支持完整 HTML（标题、段落、列表、图片、链接）。保存后前台立即生效；
          清空并保存即恢复到站点内置的「关于」模板。
        </CardDescription>
      </CardHeader>
      <CardContent class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <Button
            :variant="mode === 'edit' ? 'default' : 'outline'"
            size="sm"
            class="rounded-xl"
            @click="mode = 'edit'"
          >
            <Pencil data-icon="inline-start" />
            编辑
          </Button>
          <Button
            :variant="mode === 'preview' ? 'default' : 'outline'"
            size="sm"
            class="rounded-xl"
            @click="mode = 'preview'"
          >
            <Eye data-icon="inline-start" />
            预览
          </Button>
          <Button
            variant="ghost"
            size="sm"
            class="rounded-xl text-muted-foreground"
            :disabled="loading || saving"
            @click="resetDraft"
          >
            <RotateCcw data-icon="inline-start" />
            恢复默认模板
          </Button>
        </div>

        <Textarea
          v-if="mode === 'edit'"
          v-model="draft"
          class="min-h-[26rem] font-mono text-sm leading-relaxed"
          :disabled="loading || saving"
          placeholder="<h2>关于本站</h2>&#10;<p>这里写关于页的正文……</p>"
        />
        <div
          v-else
          class="min-h-[26rem] rounded-xl border bg-background p-6"
        >
          <!-- eslint-disable vue/no-v-html -->
          <div
            v-if="previewHtml"
            class="prose prose-sky dark:prose-invert max-w-none"
            v-html="previewHtml"
          />
          <!-- eslint-enable vue/no-v-html -->
          <p
            v-else
            class="text-sm text-muted-foreground"
          >
            正文为空：前台会展示内置的「关于」默认模板（作者卡片 + 标签页）。
          </p>
        </div>
        <p class="text-xs text-muted-foreground">
          预览与前台走同一条净化白名单：脚本、iframe、内联事件等会被剔除。
        </p>
      </CardContent>
    </Card>
  </div>
</template>
