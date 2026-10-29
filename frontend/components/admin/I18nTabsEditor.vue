<!--
  四语（zh/en/ja/zh_Hant）Tab 编辑器，v-model 兼容明文字符串（视为 zh）与 i18n dict 两种形态。
  硬契约：一旦发生编辑，update:modelValue 永远 emit 完整的 {zh,en,ja,zh_Hant} 四键 dict
  （字符串值会被升级），后端 JSON i18n 列依赖该形状；某语言缺值显示空输入框，禁止伪造默认值。
-->
<script setup lang="ts">
/* 多语言 Tab 编辑器（4 语言：zh/en/ja/zh_Hant，与项目 i18n 规则严格一致）
 *
 * v-model 兼容两种形态：
 *   a) string（历史兼容）→ 视为 zh 的值；编辑其它语言时自动升级为 {zh,en,ja,zh_Hant} 对象
 *   b) Record<string, string | null>（后端 i18n 字段标准格式）→ 直接编辑
 *   如果后端返回了部分语言缺值，显示为空 Input，不伪造默认值（符合用户要求）
 *
 * 用法：
 *   <I18nTabsEditor v-model="post.title" kind="text" label="标题" placeholder="请输入标题" />
 *   <I18nTabsEditor v-model="post.content_md" kind="markdown" label="正文 Markdown" />
 *   <I18nTabsEditor v-model="category.description" kind="textarea" rows="4" />
 *
 * kind:
 *   - text: 单行输入
 *   - textarea: 多行输入
 *   - markdown: Markdown 编辑器（带工具栏，复用 MarkdownEditor）
 *
 * translatable: 开启后每个非 zh tab 提供「一键翻译」按钮（基于 zh 值调用 /api/translate 填充）
 *
 * defineExpose 两条（只服务 kind="markdown" 的正文宿主——文章表单的「同系列文章」内链快选）：
 *   insertIntoActiveMarkdown(text) 把文本插进**当前激活语言**那个编辑器的光标处，未挂载返回 false；
 *   getActiveLocale() 给出当前 tab 的语言码，宿主据此决定内链挂不挂语言前缀。
 * Tab 因此改成受控（activeLocale，默认 zh）：观感与原先 `default-value="zh"` 完全一致，
 * 只是为了让插入知道自己该写进四个独立正文里的哪一个。
 */
import { computed, ref, watch } from 'vue'
import { Tabs, TabsContent } from '~~/components/ui/tabs'
import AdminTabList from '~~/components/admin/AdminTabList.vue'
import AdminTabTrigger from '~~/components/admin/AdminTabTrigger.vue'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Button } from '~~/components/ui/button'
import MarkdownEditor from './MarkdownEditor.vue'
import { translateAdminText } from '~~/composables/useAdminManage'
import { EMPTY_I18N_DICT } from '~~/composables/useAdminI18n'
import { Languages, Loader2 } from '@lucide/vue'

type I18nValue = string | null | Record<string, string | null>

const props = withDefaults(defineProps<{
  modelValue?: I18nValue
  kind?: 'text' | 'textarea' | 'markdown'
  label?: string
  placeholder?: string
  rows?: number
  required?: boolean
  translatable?: boolean
  /** 嵌入到 AdminFormSection 等已有卡片时传 true：去掉自身 card-surface 与内边距，避免卡片套卡片 */
  flat?: boolean
}>(), {
  kind: 'text',
  label: '',
  placeholder: '',
  rows: 3,
  required: false,
  translatable: true,
  flat: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: Record<string, string | null>): void
}>()

const LOCALES = [
  { key: 'zh', label: '简体中文', short: '简' },
  { key: 'en', label: 'English', short: 'EN' },
  { key: 'ja', label: '日本語', short: '日' },
  { key: 'zh_Hant', label: '繁體中文', short: '繁' }
] as const

// 归一化：把 string | null | 已有 dict 统一为 dict 形式
function normalize(v: I18nValue | undefined): Record<string, string> {
  if (v == null) return { ...EMPTY_I18N_DICT }
  if (typeof v === 'string') {
    return { zh: v, en: '', ja: '', zh_Hant: '' }
  }
  const obj = v as Record<string, string | null | undefined>
  return {
    zh: obj.zh ?? '',
    en: obj.en ?? '',
    ja: obj.ja ?? '',
    zh_Hant: obj.zh_Hant ?? ''
  }
}

const state = ref<Record<string, string>>(normalize(props.modelValue))

// 外部 modelValue 变化时同步到 state（仅当值确有差异时，避免覆盖用户正在编辑的内容）
watch(
  () => props.modelValue,
  (nv) => {
    const next = normalize(nv)
    const cur = state.value
    let changed = false
    for (const k of Object.keys(next)) {
      if ((cur[k] ?? '') !== (next[k] ?? '')) {
        changed = true
        break
      }
    }
    if (changed) state.value = next
  },
  { deep: true }
)

// 内部 state 变化时同步回父组件
watch(
  state,
  (v) => {
    emit('update:modelValue', { ...v })
  },
  { deep: true }
)

const filledCount = computed(() =>
  LOCALES.filter(l => typeof state.value[l.key] === 'string' && String(state.value[l.key]).trim() !== '').length
)

// ===== 一键翻译（基于 zh 源文本，填充目标语言）=====
const translatingLang = ref<string | null>(null)

const canTranslate = (lang: string): boolean => {
  if (!props.translatable || lang === 'zh') return false
  const zhVal = String(state.value.zh ?? '').trim()
  const targetVal = String(state.value[lang] ?? '').trim()
  return zhVal !== '' && targetVal === ''
}

async function translateLocale(lang: string) {
  if (!canTranslate(lang) || translatingLang.value) return
  translatingLang.value = lang
  try {
    const res = await translateAdminText(String(state.value.zh ?? ''), 'zh', [lang])
    const translated = res?.translations?.[lang]
    if (translated && translated.trim()) {
      state.value = { ...state.value, [lang]: translated }
    }
  } catch {
    // 静默失败：不打断编辑流；按钮仍可用重试
  } finally {
    translatingLang.value = null
  }
}

// ===== 供宿主页面程序化插入正文（kind="markdown"）=====
/**
 * 当前激活的语言 tab。默认 zh 与原先 `default-value="zh"` 行为一致，
 * 改成受控只为了下面这条插入能知道自己该写进哪一个编辑器。
 */
const activeLocale = ref<string>('zh')

/**
 * 每个语言 tab 各挂一个 MarkdownEditor 实例（reka 的 TabsContent 会把非激活的那几个
 * 卸载掉，所以这里按 key 收集、卸载时置空，不能假设四个都在）。
 */
const markdownRefs: Record<string, { insertAtCursor: (text: string, moveCursor?: number) => void } | null> = {}

function setMarkdownRef(localeKey: string, el: unknown) {
  markdownRefs[localeKey] = (el as { insertAtCursor: (text: string, moveCursor?: number) => void } | null) ?? null
}

/**
 * 把文本插进**当前激活语言**那个正文编辑器的光标处。
 * 为什么必须按 tab 定位：正文是四个互相独立的字符串，插错 tab 等于把链接写进
 * 另一份语言的正文里，作者在当前 tab 看不见，表现就是"点了没反应"。
 * 返回 false 表示当前 tab 的编辑器还没挂上来（非 markdown 形态、或 tab 刚切换未挂载），
 * 调用方据此提示，不要静默成功。
 */
function insertIntoActiveMarkdown(text: string): boolean {
  const editor = markdownRefs[activeLocale.value]
  if (!editor) return false
  editor.insertAtCursor(text)
  return true
}

defineExpose({ insertIntoActiveMarkdown, getActiveLocale: () => activeLocale.value })
</script>

<template>
  <div
    class="flex flex-col gap-2"
    :class="flat ? '' : 'card-surface no-glow p-3 md:p-4'"
  >
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <Label
          v-if="label"
          class="text-sm font-medium text-foreground/90 whitespace-nowrap"
        >
          {{ label }}
          <span
            v-if="required"
            class="text-destructive ml-0.5"
          >
            *
          </span>
        </Label>
      </div>
      <Badge
        variant="outline"
        class="rounded-full h-5 px-2 text-[11px] shrink-0"
      >
        {{ filledCount }} / 4 语言已填写
      </Badge>
    </div>

    <Tabs
      :model-value="activeLocale"
      @update:model-value="(v: string | number) => activeLocale = String(v)"
    >
      <AdminTabList class="grid grid-cols-4 w-full h-9 rounded-[10px]">
        <AdminTabTrigger
          v-for="l in LOCALES"
          :key="l.key"
          :value="l.key"
          class="h-8 px-1 text-xs data-[state=active]:shadow-none"
        >
          <span class="mr-1 opacity-70">{{ l.short }}</span>
          <span class="hidden sm:inline">{{ l.label }}</span>
        </AdminTabTrigger>
      </AdminTabList>

      <div
        v-for="l in LOCALES"
        :key="l.key"
      >
        <TabsContent
          :value="l.key"
          class="mt-3"
        >
          <div
            v-if="canTranslate(l.key)"
            class="flex justify-end mb-1.5"
          >
            <Button
              variant="outline"
              size="sm"
              :disabled="translatingLang !== null"
              class="h-7 rounded-[8px] text-xs gap-1"
              @click="translateLocale(l.key)"
            >
              <Loader2
                v-if="translatingLang === l.key"
                data-icon="inline-start"
                class="animate-spin"
              />
              <Languages
                v-else
                data-icon="inline-start"
              />
              从简体中文翻译
            </Button>
          </div>
          <Input
            v-if="kind === 'text'"
            v-model="state[l.key]"
            :placeholder="placeholder ? `${placeholder}（${l.label}）` : `${l.label}`"
          />
          <Textarea
            v-else-if="kind === 'textarea'"
            v-model="state[l.key]"
            :placeholder="placeholder ? `${placeholder}（${l.label}）` : `${l.label}`"
            :rows="rows"
          />
          <MarkdownEditor
            v-else
            :ref="(el: unknown) => setMarkdownRef(l.key, el)"
            v-model="state[l.key]"
            :placeholder="placeholder ? `${placeholder}（${l.label}）` : `${l.label}`"
          />
        </TabsContent>
      </div>
    </Tabs>
  </div>
</template>
