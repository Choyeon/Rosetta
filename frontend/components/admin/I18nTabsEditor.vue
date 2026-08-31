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
 */
import { computed, ref, watch } from 'vue'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Button } from '~~/components/ui/button'
import MarkdownEditor from './MarkdownEditor.vue'
import { translateAdminText } from '~~/composables/useAdminManage'
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
}>(), {
  kind: 'text',
  label: '',
  placeholder: '',
  rows: 3,
  required: false,
  translatable: true
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
  if (v == null) return { zh: '', en: '', ja: '', zh_Hant: '' }
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
</script>

<template>
  <div class="card-surface no-glow flex flex-col gap-2 p-3 md:p-4">
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

    <Tabs default-value="zh">
      <TabsList class="grid grid-cols-4 w-full h-9 rounded-[10px]">
        <TabsTrigger
          v-for="l in LOCALES"
          :key="l.key"
          :value="l.key"
          class="h-8 text-xs data-[state=active]:shadow-none"
        >
          <span class="mr-1 opacity-70">{{ l.short }}</span>
          <span class="hidden sm:inline">{{ l.label }}</span>
        </TabsTrigger>
      </TabsList>

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
                class="size-3.5 animate-spin"
              />
              <Languages
                v-else
                class="size-3.5"
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
            v-model="state[l.key]"
            :placeholder="placeholder ? `${placeholder}（${l.label}）` : `${l.label}`"
          />
        </TabsContent>
      </div>
    </Tabs>
  </div>
</template>
