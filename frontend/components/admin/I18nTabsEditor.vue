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
 *   <I18nTabsEditor v-model="post.content_md" kind="textarea" label="正文 Markdown" />
 *   <I18nTabsEditor v-model="category.description" kind="textarea" rows="4" />
 *
 * 本组件是"受控模式下的纯 Form field 组件"：它不对外发起 API，只负责把 modelValue 在 4 种语言之间同步。
 */
import { computed, watch } from 'vue'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'

type I18nValue = string | null | Record<string, string | null>

const props = withDefaults(defineProps<{
  modelValue?: I18nValue
  kind?: 'text' | 'textarea'
  label?: string
  placeholder?: string
  rows?: number
  required?: boolean
}>(), {
  kind: 'text',
  label: '',
  placeholder: '',
  rows: 3,
  required: false
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
function normalize(v: I18nValue | undefined): Record<string, string | null> {
  if (v == null) return { zh: '', en: '', ja: '', zh_Hant: '' }
  if (typeof v === 'string') {
    return { zh: v, en: '', ja: '', zh_Hant: '' }
  }
  const obj = v as Record<string, string | null>
  return {
    zh: obj.zh ?? '',
    en: obj.en ?? '',
    ja: obj.ja ?? '',
    zh_Hant: obj.zh_Hant ?? ''
  }
}

const state = ref<Record<string, string | null>>(normalize(props.modelValue))

watch(
  () => props.modelValue,
  (nv) => {
    const next = normalize(nv)
    // 仅在外部确实变化了才覆盖（避免用户输入中的内容被重新初始化）
    for (const k of Object.keys(next)) {
      if (state.value[k] !== next[k]) {
        state.value = next
        break
      }
    }
  },
  { deep: true }
)

function setLocale(lang: string, val: string | number) {
  state.value = { ...state.value, [lang]: String(val) }
  emit('update:modelValue', state.value)
}

const filledCount = computed(() =>
  LOCALES.filter(l => typeof state.value[l.key] === 'string' && String(state.value[l.key]).trim() !== '').length
)
</script>

<template>
  <div class="card-surface space-y-2 p-3 md:p-4">
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
          <Input
            v-if="kind === 'text'"
            :value="(state[l.key] ?? '') as string"
            :placeholder="placeholder ? `${placeholder}（${l.label}）` : `${l.label}`"
            @update:model-value="(v: string | number) => setLocale(l.key, v)"
          />
          <Textarea
            v-else
            :value="(state[l.key] ?? '') as string"
            :placeholder="placeholder ? `${placeholder}（${l.label}）` : `${l.label}`"
            :rows="rows"
            @update:model-value="(v: string | number) => setLocale(l.key, v)"
          />
        </TabsContent>
      </div>
    </Tabs>
  </div>
</template>
