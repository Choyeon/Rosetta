<!--
  短代码管理页：列出注册表（含归属来源）、注册/删除「字符串模板」式短代码、预览渲染结果。
  契约（后端 906e117a 收口后的口径，改任一字段前先读）：
  - GET  /admin/shortcodes      → {success, data: {count, items[], persisted}}；items 的
    `plugin` 非空即插件归属（只读），`template` 真即本页 API 注册的模板（可删）。
    列表本身就是「多 worker 重放点」：另一个进程写的模板在这里必然看得见。
  - POST /admin/shortcodes/register / DELETE /admin/shortcodes/{tag}
    对插件归属 tag 一律 409 SHORTCODE_PLUGIN_OWNED —— UI 必须把它翻成人话，
    否则管理员只会看到一个像 bug 的"删除失败"。
  - POST /admin/shortcodes（预览）是唯一能带 context 的入口；访客侧的
    /shortcodes/render 故意不收 context，别在这里把 ctx 当成"渲染任意 HTML 的工具"。
  - apiFetch 不解信封：读数一律 res.data.xxx；错误经拦截器 toast 后重抛，
    页内再留一条内联错误态供重试（静默失败是 bug，双报同一条消息也是）。
  - 预览结果**绝不 v-html**：handler 输出虽过引擎白名单，但把它插进后台 DOM
    等于给运营期数据开一个绕过前端框架的注入口，用 <pre> 当纯文本看即可。
  - 删除走两步内联确认（不引入新 dialog 组件），确认态是组件内局部状态。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="短代码"
      description="查看当前注册的短代码，注册简单的「字符串模板」式短代码并预览渲染结果"
      :icon="Code2"
    />

    <Alert
      v-if="listError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>短代码列表获取失败</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ listError }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          :disabled="loading"
          @click="loadList"
        >
          <RefreshCw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <div class="grid grid-cols-3 gap-4">
      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-1 p-5">
          <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
            已注册短代码
          </p>
          <Skeleton
            v-if="loading && list == null"
            class="h-8 w-16 rounded-lg"
          />
          <div
            v-else
            class="text-2xl font-bold tabular-nums tracking-tight"
          >
            {{ listError ? '—' : (list?.count ?? 0) }}
          </div>
        </div>
      </AdminCard>
      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-1 p-5">
          <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
            本页注册的模板
          </p>
          <div
            v-if="!listError"
            class="text-2xl font-bold tabular-nums tracking-tight"
          >
            {{ list?.persisted ?? 0 }}
          </div>
          <div
            v-else
            class="text-2xl font-bold"
          >
            —
          </div>
          <p class="text-xs text-muted-foreground">
            存于站点配置，重启与多进程间自动重放
          </p>
        </div>
      </AdminCard>
      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-1 p-5">
          <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
            插件自带（只读）
          </p>
          <div class="text-2xl font-bold tabular-nums tracking-tight">
            {{ pluginOwnedCount }}
          </div>
          <p class="text-xs text-muted-foreground">
            由插件代码注册，随插件启停，不能在此覆盖或删除
          </p>
        </div>
      </AdminCard>
    </div>

    <AdminCard class="rounded-2xl overflow-hidden">
      <div class="flex items-center justify-between gap-3 p-5 pb-3">
        <h3 class="font-semibold tracking-tight">
          注册表
        </h3>
        <Button
          variant="ghost"
          size="sm"
          class="rounded-lg"
          :disabled="loading"
          @click="loadList"
        >
          <RefreshCw data-icon="inline-start" />
          刷新
        </Button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-xs uppercase text-muted-foreground">
            <tr class="border-b">
              <th class="text-left font-medium px-5 py-2">
                标签
              </th>
              <th class="text-left font-medium px-3 py-2">
                来源
              </th>
              <th class="text-left font-medium px-3 py-2">
                配对
              </th>
              <th class="text-left font-medium px-3 py-2">
                描述
              </th>
              <th class="text-right font-medium px-5 py-2">
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in sortedItems"
              :key="item.tag"
              class="border-b last:border-0"
            >
              <td class="px-5 py-2.5 font-mono">
                [{{ item.tag }}]
              </td>
              <td class="px-3 py-2.5">
                <Badge
                  :variant="item.plugin ? 'secondary' : 'outline'"
                  class="rounded-md"
                >
                  {{ item.plugin ? `插件 ${item.plugin}` : (item.template ? '模板' : '内建') }}
                </Badge>
              </td>
              <td class="px-3 py-2.5 text-muted-foreground">
                {{ item.has_paired ? '[x]…[/x]' : '[x /]' }}
              </td>
              <td class="px-3 py-2.5 text-muted-foreground max-w-[28rem] truncate">
                {{ item.description || '—' }}
              </td>
              <td class="px-5 py-2.5 text-right">
                <span
                  v-if="item.plugin"
                  class="text-xs text-muted-foreground"
                >
                  随插件管理
                </span>
                <div
                  v-else-if="pendingDelete !== item.tag"
                  class="flex items-center justify-end gap-2"
                >
                  <Button
                    variant="outline"
                    size="sm"
                    class="rounded-lg"
                    @click="fillPreview(item.tag)"
                  >
                    预览
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    class="rounded-lg"
                    @click="pendingDelete = item.tag"
                  >
                    <Trash2 data-icon="inline-start" />
                    删除
                  </Button>
                </div>
                <div
                  v-else
                  class="flex items-center justify-end gap-2"
                >
                  <span class="text-xs text-destructive">确认删除 [{{ item.tag }}]？</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    class="rounded-lg"
                    @click="pendingDelete = null"
                  >
                    取消
                  </Button>
                  <Button
                    size="sm"
                    class="rounded-lg"
                    :disabled="deleting"
                    @click="removeTemplate(item.tag)"
                  >
                    确认
                  </Button>
                </div>
              </td>
            </tr>
            <tr v-if="!sortedItems.length">
              <td
                colspan="5"
                class="px-5 py-8 text-center text-muted-foreground"
              >
                {{ loading ? '加载中…' : '注册表为空' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </AdminCard>

    <div class="grid gap-5 lg:grid-cols-2">
      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-4 p-5">
          <div>
            <h3 class="font-semibold tracking-tight">
              注册模板短代码
            </h3>
            <p class="text-xs text-muted-foreground mt-1">
              替换文本里的 <code class="font-mono">{content}</code> 会被成对短代码的正文替换，
              <code class="font-mono">{属性名}</code> 会被对应属性值替换。
            </p>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="shortcode-tag"
              class="text-xs text-muted-foreground"
            >
              标签名
            </Label>
            <Input
              id="shortcode-tag"
              v-model="form.tag"
              placeholder="cta"
              maxlength="50"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="shortcode-replacement"
              class="text-xs text-muted-foreground"
            >
              替换文本
            </Label>
            <Textarea
              id="shortcode-replacement"
              v-model="form.replacement"
              class="min-h-24 font-mono text-xs"
              placeholder="<a class=&quot;cta&quot; href=&quot;{url}&quot;>{content}</a>"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="shortcode-description"
              class="text-xs text-muted-foreground"
            >
              描述（可选）
            </Label>
            <Input
              id="shortcode-description"
              v-model="form.description"
              placeholder="行动号召按钮"
              maxlength="200"
            />
          </div>
          <div class="flex items-center gap-2">
            <Button
              class="rounded-lg"
              :disabled="registering || !canRegister"
              @click="registerTemplate"
            >
              <Plus data-icon="inline-start" />
              注册
            </Button>
            <p
              v-if="registerError"
              class="text-xs text-destructive"
            >
              {{ registerError }}
            </p>
          </div>
        </div>
      </AdminCard>

      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-4 p-5">
          <div>
            <h3 class="font-semibold tracking-tight">
              预览渲染结果
            </h3>
            <p class="text-xs text-muted-foreground mt-1">
              走的是与文章正文相同的引擎与输出白名单；结果为纯文本展示，不会在本页执行脚本。
            </p>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="shortcode-content"
              class="text-xs text-muted-foreground"
            >
              含短代码的文本
            </Label>
            <Textarea
              id="shortcode-content"
              v-model="previewContent"
              class="min-h-24 font-mono text-xs"
              placeholder="[cta url=&quot;/docs&quot;]查看文档[/cta]"
            />
          </div>
          <Button
            variant="outline"
            class="rounded-lg w-fit"
            :disabled="previewing"
            @click="runPreview"
          >
            <Code2 data-icon="inline-start" />
            渲染
          </Button>
          <div
            v-if="previewResult"
            class="flex flex-col gap-2"
          >
            <p class="text-xs text-muted-foreground">
              {{ previewResult.original_length }} → {{ previewResult.rendered_length }} 字符
            </p>
            <pre
              class="max-h-64 overflow-auto rounded-xl border bg-muted/40 p-3 text-xs whitespace-pre-wrap break-all"
            >{{ previewResult.rendered }}</pre>
          </div>
          <p
            v-else-if="previewError"
            class="text-xs text-destructive"
          >
            {{ previewError }}
          </p>
        </div>
      </AdminCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiFetch } from '~~/composables/useApi'
import { extractApiErrorMessage } from '~~/lib/utils'
import { AlertTriangle, Code2, Plus, RefreshCw, Trash2 } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Textarea } from '~~/components/ui/textarea'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Skeleton } from '~~/components/ui/skeleton'
import AdminCard from '~~/components/admin/AdminCard.vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'

definePageMeta({ ssr: false, layout: 'admin' })

interface ShortcodeDefinition {
  tag: string
  has_paired: boolean
  description: string | null
  plugin: string | null
  template: boolean
}
interface ShortcodeListData {
  count: number
  items: ShortcodeDefinition[]
  persisted: number
}
interface ShortcodePreviewData {
  rendered: string
  original_length: number
  rendered_length: number
}
type Envelope<T> = { success: boolean, data: T, message?: string }

const LIST_URL = '/admin/shortcodes'
const REGISTER_URL = '/admin/shortcodes/register'
/** 与标签名正则同源（后端 ShortcodeRegisterRequest.tag.pattern），不一致会让用户白填一次 */
const TAG_PATTERN = /^[A-Za-z_][A-Za-z0-9_-]*$/

const list = ref<ShortcodeListData | null>(null)
const loading = ref(false)
const listError = ref<string | null>(null)

const form = ref({ tag: '', replacement: '', description: '' })
const registering = ref(false)
const registerError = ref<string | null>(null)

const deleting = ref(false)
const pendingDelete = ref<string | null>(null)

const previewContent = ref('')
const previewing = ref(false)
const previewResult = ref<ShortcodePreviewData | null>(null)
const previewError = ref<string | null>(null)

const sortedItems = computed(() =>
  [...(list.value?.items ?? [])].sort((a, b) => a.tag.localeCompare(b.tag))
)
const pluginOwnedCount = computed(
  () => (list.value?.items ?? []).filter(item => item.plugin).length
)
const canRegister = computed(
  () => TAG_PATTERN.test(form.value.tag.trim()) && form.value.replacement !== ''
)

/** 409 单独成句：它是设计如此的所有权护栏，不说清就像接口坏了 */
function describeError(err: unknown, fallback: string): string {
  const e = err as { status?: number, data?: unknown }
  if (e?.status === 409) {
    return '该标签由插件注册，插件页才是它的管理入口；这里既不能覆盖也不能删除。'
  }
  return extractApiErrorMessage(e?.data, fallback)
}

async function loadList() {
  loading.value = true
  listError.value = null
  try {
    const res = await apiFetch<Envelope<ShortcodeListData>>(LIST_URL, { silentToast: true })
    list.value = res.data
  } catch (err) {
    listError.value = describeError(err, '无法读取短代码注册表')
  } finally {
    loading.value = false
  }
}

async function registerTemplate() {
  if (!canRegister.value) {
    return
  }
  registering.value = true
  registerError.value = null
  const tag = form.value.tag.trim()
  try {
    const res = await apiFetch<Envelope<ShortcodeListData>>(
      REGISTER_URL,
      {
        method: 'POST',
        silentToast: true,
        body: {
          tag,
          replacement: form.value.replacement,
          description: form.value.description.trim() || null
        }
      }
    )
    list.value = res.data
    form.value = { tag: '', replacement: '', description: '' }
    if (!previewContent.value.includes(tag)) {
      previewContent.value = `[${tag}]在这里填写正文[/${tag}]`
    }
  } catch (err) {
    registerError.value = describeError(err, '注册失败')
  } finally {
    registering.value = false
  }
}

async function removeTemplate(tag: string) {
  deleting.value = true
  try {
    await apiFetch(`${LIST_URL}/${encodeURIComponent(tag)}`, { method: 'DELETE' })
    await loadList()
  } catch {
    // apiFetch 已 toast；列表保持原状，用户看得见失败条目
  } finally {
    deleting.value = false
    pendingDelete.value = null
  }
}

function fillPreview(tag: string) {
  previewContent.value = `[${tag}]示例内容[/${tag}]`
  void runPreview()
}

async function runPreview() {
  if (!previewContent.value) {
    previewResult.value = null
    previewError.value = '请先填写要渲染的文本'
    return
  }
  previewing.value = true
  previewError.value = null
  try {
    const res = await apiFetch<Envelope<ShortcodePreviewData>>(
      LIST_URL,
      { method: 'POST', silentToast: true, body: { content: previewContent.value } }
    )
    previewResult.value = res.data
  } catch (err) {
    previewResult.value = null
    previewError.value = describeError(err, '渲染失败')
  } finally {
    previewing.value = false
  }
}

onMounted(loadList)
</script>
