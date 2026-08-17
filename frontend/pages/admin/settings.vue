<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-3xl font-bold tracking-tight font-display">
          {{ t('admin.settings.title') }}
        </h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ t('admin.settings.desc') }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <Select v-model="activeGroup">
          <SelectTrigger class="w-56">
            <SelectValue :placeholder="t('admin.settings.selectGroup')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              v-for="g in groupKeys"
              :key="g"
              :value="g"
            >
              {{ groupLabel(g) }}
            </SelectItem>
          </SelectContent>
        </Select>
        <Button
          :disabled="loading || saving || !activeGroup"
          @click="save"
        >
          <Save class="mr-2 size-4" />
          {{ saving ? t('admin.settings.saving') : t('admin.settings.save') }}
        </Button>
      </div>
    </div>

    <!-- 错误重试 -->
    <div
      v-if="loadError"
      class="flex flex-col items-start gap-3"
    >
      <Alert variant="destructive">
        <AlertCircle class="size-4" />
        <AlertTitle>{{ t('admin.settings.loadFailed') }}</AlertTitle>
        <AlertDescription>{{ loadError }}</AlertDescription>
      </Alert>
      <Button
        variant="outline"
        size="sm"
        :disabled="loading"
        @click="load"
      >
        <RefreshCw
          class="mr-2 size-4"
          :class="{ 'animate-spin': loading }"
        />
        {{ t('admin.settings.retry') }}
      </Button>
    </div>

    <Card v-else>
      <CardHeader>
        <CardTitle class="text-xl">
          {{ groupLabel(activeGroup) }}
        </CardTitle>
        <CardDescription>{{ t('admin.settings.groupDesc', { group: activeGroup }) }}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="loading"
          class="space-y-4"
        >
          <Skeleton
            v-for="i in 6"
            :key="i"
            class="h-12 w-full"
          />
        </div>

        <div
          v-else-if="formFields.length > 0"
          class="space-y-5 max-w-2xl"
        >
          <div
            v-for="field in formFields"
            :key="field.key"
            class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4"
          >
            <Label
              :for="`set-${field.key}`"
              class="sm:w-56 shrink-0 font-medium break-all"
            >
              {{ field.key }}
            </Label>

            <div class="flex-1 min-w-0">
              <!-- 布尔值：开关 -->
              <div
                v-if="field.kind === 'boolean'"
                class="flex items-center gap-2"
              >
                <Switch
                  :id="`set-${field.key}`"
                  :model-value="field.value === true"
                  @update:model-value="(v: boolean) => (draft[field.key] = v)"
                />
                <span class="text-xs text-muted-foreground">
                  {{ field.value === true ? t('admin.settings.enabled') : t('admin.settings.disabled') }}
                </span>
              </div>

              <!-- 数字 -->
              <Input
                v-else-if="field.kind === 'number'"
                :id="`set-${field.key}`"
                type="number"
                :model-value="draft[field.key]"
                @update:model-value="(v: string | number) => (draft[field.key] = v)"
              />

              <!-- 敏感项：只读展示 -->
              <Input
                v-else-if="field.kind === 'sensitive'"
                :id="`set-${field.key}`"
                :model-value="field.value === null || field.value === undefined ? '' : String(field.value)"
                type="password"
                readonly
                class="opacity-80"
              />

              <!-- 对象 / 数组：JSON 文本域 -->
              <Textarea
                v-else-if="field.kind === 'json'"
                :id="`set-${field.key}`"
                v-model="jsonTexts[field.key]"
                rows="3"
                class="font-mono text-xs"
              />

              <!-- 普通字符串 -->
              <Input
                v-else
                :id="`set-${field.key}`"
                :model-value="draft[field.key] === null || draft[field.key] === undefined ? '' : String(draft[field.key])"
                @update:model-value="(v: string | number) => (draft[field.key] = v)"
              />

              <p
                v-if="field.kind === 'sensitive'"
                class="text-xs text-muted-foreground mt-1"
              >
                {{ t('admin.settings.sensitiveHint') }}
              </p>
              <p
                v-else-if="field.kind === 'json'"
                class="text-xs text-muted-foreground mt-1"
              >
                {{ t('admin.settings.jsonHint') }}
              </p>
            </div>
          </div>
        </div>

        <div
          v-else
          class="flex flex-col items-center justify-center py-16 text-muted-foreground"
        >
          <Settings2 class="size-8 mb-2" />
          <p class="text-sm">
            {{ t('admin.settings.emptyGroup') }}
          </p>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import { Switch } from '~~/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import {
  Alert,
  AlertDescription,
  AlertTitle
} from '~~/components/ui/alert'
import { Save, RefreshCw, AlertCircle, Settings2 } from '@lucide/vue'
import {
  fetchAllSettings,
  isSensitiveSettingKey,
  saveSettingsGroup,
  type AllSettingsGroups,
  type SettingsGroupData,
  type SettingsValue
} from '~~/composables/useAdminManage'

definePageMeta({
  layout: 'admin'
})

const { t } = useI18n()
const toast = useToast()

/** 后端 SETTING_GROUPS_17 的固定顺序 */
const GROUP_ORDER = [
  'basic',
  'reading',
  'comments',
  'media',
  'seo',
  'email',
  'cdn',
  'cache',
  'security',
  'features',
  'appearance',
  'navigation',
  'friendlinks',
  'hero',
  'notice',
  'sidebar',
  'footer'
] as const

const groups = ref<AllSettingsGroups>({})
const groupKeys = ref<string[]>([])
const activeGroup = ref('basic')
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)

const draft = ref<SettingsGroupData>({})
const jsonTexts = ref<Record<string, string>>({})

type FieldKind = 'boolean' | 'number' | 'sensitive' | 'json' | 'string'

interface FormField {
  key: string
  kind: FieldKind
  value: SettingsValue
}

const formFields = computed<FormField[]>(() => {
  const data = groups.value[activeGroup.value]
  if (!data) return []
  return Object.entries(data).map(([key, value]) => {
    let kind: FieldKind = 'string'
    if (isSensitiveSettingKey(key)) kind = 'sensitive'
    else if (typeof value === 'boolean') kind = 'boolean'
    else if (typeof value === 'number') kind = 'number'
    else if (Array.isArray(value) || (typeof value === 'object' && value !== null)) kind = 'json'
    return { key, kind, value }
  })
})

function groupLabel(group: string): string {
  const key = `admin.settings.groups.${group}`
  const label = t(key)
  return label === key ? group : label
}

function syncDraft(): void {
  const data = groups.value[activeGroup.value] ?? {}
  const next: SettingsGroupData = {}
  const nextJson: Record<string, string> = {}
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value) || (typeof value === 'object' && value !== null)) {
      nextJson[key] = JSON.stringify(value, null, 2)
    } else {
      next[key] = value
    }
  }
  draft.value = next
  jsonTexts.value = nextJson
}

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const all = await fetchAllSettings()
    groups.value = all
    groupKeys.value = GROUP_ORDER.filter(g => g in all)
    if (!groupKeys.value.includes(activeGroup.value)) {
      activeGroup.value = groupKeys.value[0] ?? 'basic'
    }
    syncDraft()
  } catch (err) {
    const e = err as { data?: { message?: string, detail?: unknown } }
    loadError.value = (e?.data?.message
      ?? (typeof e?.data?.detail === 'string' ? e.data.detail : ''))
    || (err instanceof Error ? err.message : String(err))
  } finally {
    loading.value = false
  }
}

function buildPayload(): SettingsGroupData | null {
  const original = groups.value[activeGroup.value] ?? {}
  const payload: SettingsGroupData = {}

  for (const [key, value] of Object.entries(draft.value)) {
    if (isSensitiveSettingKey(key)) {
      // 敏感项只读：原样回传，避免明文覆盖
      payload[key] = original[key] ?? ''
      continue
    }
    if (typeof original[key] === 'number') {
      const n = Number(value)
      if (Number.isNaN(n)) {
        toast.error(t('admin.settings.invalidNumber', { key }))
        return null
      }
      payload[key] = n
    } else {
      payload[key] = value
    }
  }

  for (const [key, text] of Object.entries(jsonTexts.value)) {
    const originalText = JSON.stringify(original[key] ?? null, null, 2)
    if (text.trim() === originalText.trim()) {
      payload[key] = original[key]
      continue
    }
    try {
      payload[key] = JSON.parse(text) as SettingsValue
    } catch {
      toast.error(t('admin.settings.invalidJson', { key }))
      return null
    }
  }

  return payload
}

async function save(): Promise<void> {
  const payload = buildPayload()
  if (payload === null) return
  saving.value = true
  try {
    const res = await saveSettingsGroup(activeGroup.value, payload)
    if (res.data) {
      groups.value = { ...groups.value, [activeGroup.value]: res.data }
      syncDraft()
    }
    toast.success(t('admin.settings.toast.saved', { n: res.changed?.length ?? 0 }))
  } catch {
    // apiFetch 已 toast
  } finally {
    saving.value = false
  }
}

watch(activeGroup, () => {
  if (!loading.value) syncDraft()
})

onMounted(() => {
  load()
})
</script>
