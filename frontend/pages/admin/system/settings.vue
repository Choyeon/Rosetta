<!--
  站点设置页：按组分栏编辑后端返回的全部站点配置，表单控件由值类型反向推断（inferSchema），保存以单组为粒度。
  契约：与主题 Customizer 重复的键（primary_color / hero.title / footer.copyright 等）不仅 UI 屏蔽，保存 payload 也必须强制剥离，防止站点设置回写覆盖主题色（双写冲突）；
  isDirty 只对比当前激活组与最近一次服务端回包。分组键集以后端 _default_<group>() 为唯一清单，
  没有执行点的开关不得出现在这里（回归见 tests/test_settings_group_consumers.py）。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="站点设置"
      description="配置 Rosetta 博客系统的全部参数"
      :icon="Settings"
    >
      <template #actions>
        <Badge :variant="isDirty ? 'warning' : 'success'">
          <span
            class="size-1.5 shrink-0 rounded-full"
            :class="isDirty ? 'bg-warning animate-pulse' : 'bg-success'"
          />
          {{ isDirty ? '有未保存改动' : '已保存' }}
        </Badge>
        <Button
          size="sm"
          :disabled="!isDirty || saving"
          class="shadow-sm"
          @click="handleSaveCurrentGroup"
        >
          <Save
            v-if="!saving"
            data-icon="inline-start"
          />
          <Loader2
            v-else
            data-icon="inline-start"
            class="animate-spin"
          />
          保存当前组
        </Button>
      </template>
    </AdminPageHeader>

    <div
      v-if="loading"
      class="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6 h-auto md:h-[calc(100vh-220px)]"
    >
      <ScrollArea class="card-surface p-3">
        <div class="flex flex-col gap-2">
          <Skeleton
            v-for="i in 17"
            :key="i"
            class="h-10 rounded-lg"
          />
        </div>
      </ScrollArea>
      <AdminCard>
        <Skeleton class="h-8 w-48 rounded mb-6" />
        <div class="flex flex-col gap-4">
          <Skeleton
            v-for="i in 6"
            :key="i"
            class="h-14 rounded-lg"
          />
        </div>
      </AdminCard>
    </div>

    <Alert
      v-if="!loading && loadError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>站点配置加载失败</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ loadError }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          @click="loadAll"
        >
          <RotateCcw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6 h-auto md:h-[calc(100vh-220px)]"
    >
      <ScrollArea class="card-surface p-2">
        <div class="flex flex-col gap-1 p-1">
          <button
            v-for="g in groups"
            :key="g.key"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left"
            :class="activeGroup === g.key
              ? 'bg-primary text-primary-foreground shadow-md'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
            @click="activeGroup = g.key"
          >
            <component
              :is="g.icon"
              class="size-4 shrink-0"
            />
            <span class="truncate">{{ g.label }}</span>
          </button>
        </div>
      </ScrollArea>

      <ScrollArea class="card-surface">
        <div
          class="flex flex-col gap-6 p-6"
        >
          <div class="flex flex-col gap-1">
            <h2 class="text-lg font-bold">
              {{ currentGroupMeta?.label }}
            </h2>
            <p class="text-sm text-muted-foreground">
              {{ currentGroupMeta?.desc }}
            </p>
          </div>
          <Separator />
          <div class="flex flex-col gap-5 max-w-3xl">
            <template
              v-for="(schema, key) in currentGroupSchemas"
              :key="key"
            >
              <template v-if="schema.type === 'string' && !schema.long && !schema.sensitive">
                <div class="flex flex-col gap-2">
                  <Label
                    :for="`set-${key}`"
                    class="text-sm font-medium"
                  >{{ schema.label }}</Label>
                  <Input
                    :id="`set-${key}`"
                    v-model="strRef(key).value"
                    :placeholder="schema.placeholder || ''"
                    class="rounded-xl"
                  />
                  <p
                    v-if="schema.help"
                    class="text-xs text-muted-foreground"
                  >
                    {{ schema.help }}
                  </p>
                </div>
              </template>

              <template v-else-if="schema.type === 'string' && schema.sensitive">
                <div class="flex flex-col gap-2">
                  <Label
                    :for="`set-${key}`"
                    class="text-sm font-medium"
                  >{{ schema.label }}</Label>
                  <div class="relative">
                    <Input
                      :id="`set-${key}`"
                      v-model="strRef(key).value"
                      :type="showSensitive[key] ? 'text' : 'password'"
                      :placeholder="schema.placeholder || ''"
                      class="rounded-xl pr-11"
                    />
                    <button
                      type="button"
                      class="absolute right-2 top-1/2 -translate-y-1/2 size-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                      :aria-label="showSensitive[key] ? '隐藏敏感值' : '显示敏感值'"
                      @click="toggleSensitive(key)"
                    >
                      <Eye
                        v-if="!showSensitive[key]"
                        class="size-4"
                      />
                      <EyeOff
                        v-else
                        class="size-4"
                      />
                    </button>
                  </div>
                  <p
                    v-if="schema.help"
                    class="text-xs text-muted-foreground"
                  >
                    {{ schema.help }}
                  </p>
                </div>
              </template>

              <template v-else-if="schema.type === 'string' && schema.long">
                <div class="flex flex-col gap-2">
                  <Label
                    :for="`set-${key}`"
                    class="text-sm font-medium"
                  >{{ schema.label }}</Label>
                  <Textarea
                    :id="`set-${key}`"
                    v-model="strRef(key).value"
                    :placeholder="schema.placeholder || ''"
                    rows="4"
                    class="rounded-xl resize-none"
                  />
                  <p
                    v-if="schema.help"
                    class="text-xs text-muted-foreground"
                  >
                    {{ schema.help }}
                  </p>
                </div>
              </template>

              <template v-else-if="schema.type === 'json'">
                <div class="flex flex-col gap-2">
                  <Label
                    :for="`set-${key}`"
                    class="text-sm font-medium"
                  >{{ schema.label }}</Label>
                  <Textarea
                    :id="`set-${key}`"
                    :model-value="stringifyJson(formState[activeGroup]?.[key] ?? null)"
                    rows="8"
                    class="rounded-xl resize-none font-mono text-xs"
                    placeholder="[]"
                    @update:model-value="parseJsonInput(key, String($event))"
                  />
                  <p class="text-xs text-muted-foreground">
                    JSON 数组格式{{ schema.help ? '，' + schema.help : '' }}
                  </p>
                </div>
              </template>

              <template v-else-if="schema.type === 'number'">
                <div class="flex flex-col gap-2">
                  <Label
                    :for="`set-${key}`"
                    class="text-sm font-medium"
                  >{{ schema.label }}</Label>
                  <Input
                    :id="`set-${key}`"
                    v-model.number="numRef(key).value"
                    type="number"
                    :min="schema.min"
                    :max="schema.max"
                    :placeholder="schema.placeholder || ''"
                    class="rounded-xl"
                  />
                  <p
                    v-if="schema.help"
                    class="text-xs text-muted-foreground"
                  >
                    {{ schema.help }}
                  </p>
                </div>
              </template>

              <template v-else-if="schema.type === 'boolean'">
                <div class="flex items-center justify-between rounded-xl border border-border p-4 bg-muted/30">
                  <div class="flex flex-col gap-0.5">
                    <Label
                      :for="`set-${key}`"
                      class="text-sm font-medium"
                    >{{ schema.label }}</Label>
                    <p
                      v-if="schema.help"
                      class="text-xs text-muted-foreground"
                    >
                      {{ schema.help }}
                    </p>
                  </div>
                  <Switch
                    :id="`set-${key}`"
                    v-model="boolRef(key).value"
                  />
                </div>
              </template>

              <template v-else-if="schema.type === 'color'">
                <div class="flex flex-col gap-2">
                  <Label
                    :for="`set-${key}`"
                    class="text-sm font-medium"
                  >{{ schema.label }}</Label>
                  <div class="flex items-center gap-3">
                    <div class="relative">
                      <input
                        v-model="colorRef(key).value"
                        type="color"
                        :aria-label="`${schema.label} 取色器`"
                        class="absolute inset-0 opacity-0 cursor-pointer size-11 rounded-xl"
                      >
                      <div
                        class="size-11 rounded-xl border border-border shadow-inner"
                        :style="{ background: colorRef(key).value || '#ffffff' }"
                      />
                    </div>
                    <Input
                      :id="`set-${key}`"
                      v-model="colorRef(key).value"
                      class="rounded-xl font-mono text-xs uppercase w-32"
                      placeholder="#0EA5A9"
                    />
                  </div>
                  <p
                    v-if="schema.help"
                    class="text-xs text-muted-foreground"
                  >
                    {{ schema.help }}
                  </p>
                </div>
              </template>
            </template>
          </div>
        </div>
      </ScrollArea>
    </div>

    <Alert
      v-if="Object.keys(formState).length === 0 && !loading && !loadError"
      variant="warning"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>暂无配置数据</AlertTitle>
      <AlertDescription>接口未返回任何设置组，请稍后刷新重试。</AlertDescription>
    </Alert>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, type WritableComputedRef } from 'vue'
import {
  fetchAllSettings,
  saveSettingsGroup,
  isSensitiveSettingKey,
  type AllSettingsGroups,
  type SettingsGroupData,
  type SettingsValue
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  Settings, Save, Loader2, Eye, EyeOff, AlertTriangle, RotateCcw,
  Globe, BookOpen, MessageSquare, Image, Search, Mail,
  Shield, ToggleLeft, Palette, Menu, Sparkles, Bell,
  LayoutTemplate
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import AdminCard from '~~/components/admin/AdminCard.vue'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Skeleton } from '~~/components/ui/skeleton'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Switch } from '~~/components/ui/switch'
import { Separator } from '~~/components/ui/separator'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

interface FieldSchema {
  label: string
  type: 'string' | 'number' | 'boolean' | 'color' | 'json'
  long?: boolean
  sensitive?: boolean
  min?: number
  max?: number
  placeholder?: string
  help?: string
}

/**
 * 后台设置分组（已精简）：
 *  - appearance 只留有真实消费方的五项（主色/强调色由主题 Customizer 覆写、
 *    宽度由首页读取、版权与 Powered by 由页脚读取）；
 *  - 代码高亮配色归 assets/css/main.css 的 --hljs-* 令牌，明/暗首帧归 localStorage.theme，
 *    字体族归 Tailwind preset，侧边栏显示与位置归主题 Customizer 的 mods，
 *    所以 code_theme / default_theme / font_family 与整个 sidebar 分组已删除。
 */
const groups = [
  { key: 'basic', label: '基础信息', icon: Globe, desc: '站点名称、副标题、描述等基础资料' },
  { key: 'reading', label: '阅读体验', icon: BookOpen, desc: '文章分页、字数统计、目录深度等' },
  { key: 'comments', label: '评论设置', icon: MessageSquare, desc: '评论开关、审核、反垃圾等' },
  { key: 'media', label: '媒体上传', icon: Image, desc: '上传大小限制、文件类型、CDN 前缀' },
  { key: 'seo', label: 'SEO 优化', icon: Search, desc: '默认标题、关键词、分析 ID 等' },
  { key: 'email', label: '邮件通知', icon: Mail, desc: 'SMTP 服务器配置、发件人设置' },
  { key: 'security', label: '安全策略', icon: Shield, desc: '登录失败次数阈值与锁定时长' },
  { key: 'features', label: '功能开关', icon: ToggleLeft, desc: '全局功能模块开关控制' },
  { key: 'appearance', label: '外观主题', icon: Palette, desc: '版权与 Powered by 标识（主色 / 强调色 / 宽度请在主题自定义中改）' },
  { key: 'navigation', label: '导航菜单', icon: Menu, desc: '导航栏样式、顶栏组件开关' },
  { key: 'hero', label: '首页横幅', icon: Sparkles, desc: 'Hero 区域标题、CTA、背景图' },
  { key: 'notice', label: '站点公告', icon: Bell, desc: '公告条类型、正文、可关闭' },
  { key: 'footer', label: '页脚', icon: LayoutTemplate, desc: '版权信息、ICP、社交链接' }
]

const activeGroup = ref('basic')
const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const originalState = ref<AllSettingsGroups>({})
const formState = reactive<AllSettingsGroups>({})
const showSensitive = reactive<Record<string, boolean>>({})

const currentGroupMeta = computed(() => groups.find(g => g.key === activeGroup.value))

const isDirty = computed(() => {
  const o = originalState.value[activeGroup.value]
  const c = formState[activeGroup.value]
  if (!o || !c) return false
  return JSON.stringify(o) !== JSON.stringify(c)
})

function toggleSensitive(key: string) {
  showSensitive[key] = !showSensitive[key]
}

function stringifyJson(v: SettingsValue): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'string') return v
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

function parseJsonInput(key: string, raw: string) {
  if (!raw.trim()) {
    formState[activeGroup.value]![key] = []
    return
  }
  try {
    formState[activeGroup.value]![key] = JSON.parse(raw)
  } catch {
    toast.warning('JSON 格式有误，请检查语法')
    formState[activeGroup.value]![key] = raw
  }
}

/**
 * 类型安全的 v-model 绑定助手：
 * formState[activeGroup][key] 的类型是 SettingsValue（联合类型），
 * 直接 v-model 到 Input/Switch 等窄类型组件会触发 TS 报错。
 * 这里用 WritableComputedRef 在读写时做窄化与兜底，保证模板干净通过类型检查。
 */
function strRef(key: string): WritableComputedRef<string> {
  return computed<string>({
    get: () => {
      const v = formState[activeGroup.value]?.[key]
      return typeof v === 'string' ? v : v == null ? '' : String(v)
    },
    set: (val) => { if (formState[activeGroup.value]) formState[activeGroup.value]![key] = val }
  })
}

function numRef(key: string): WritableComputedRef<number | undefined> {
  return computed<number | undefined>({
    get: () => {
      const v = formState[activeGroup.value]?.[key]
      if (typeof v === 'number') return v
      if (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v))) return Number(v)
      return undefined
    },
    set: (val) => { if (formState[activeGroup.value]) formState[activeGroup.value]![key] = val ?? 0 }
  })
}

function boolRef(key: string): WritableComputedRef<boolean> {
  return computed<boolean>({
    get: () => {
      const v = formState[activeGroup.value]?.[key]
      return typeof v === 'boolean' ? v : Boolean(v)
    },
    set: (val) => { if (formState[activeGroup.value]) formState[activeGroup.value]![key] = val }
  })
}

function colorRef(key: string): WritableComputedRef<string> {
  return computed<string>({
    get: () => {
      const v = formState[activeGroup.value]?.[key]
      return typeof v === 'string' && v.trim() !== '' ? v : '#ffffff'
    },
    set: (val) => { if (formState[activeGroup.value]) formState[activeGroup.value]![key] = val }
  })
}

function inferSchema(key: string, value: SettingsValue, defaults: Record<string, SettingsValue>): FieldSchema {
  const label = {
    site_name: '站点名称', subtitle: '站点副标题', logo: 'Logo 图片 URL',
    description: '站点描述', keywords: 'SEO 关键词（逗号分隔）', site_url: '站点首页 URL',
    icp_number: 'ICP 备案号',
    about_page_html: '关于页面完整 HTML（直接渲染，优先级高于默认 Tabs 结构）',
    posts_per_page: '每页文章数', show_reading_time: '显示预估阅读时间',
    show_word_count: '显示字数统计', show_toc: '启用文章目录',
    toc_depth: '目录最大层级深度', line_height: '正文行高（倍）',
    font_size: '正文字号（px）',
    enable: '启用评论功能', require_approval: '新评论需审核',
    allow_guest: '允许访客匿名评论', max_length: '评论最大字符数',
    enable_antispam: '启用反垃圾过滤', enable_nested: '启用嵌套回复',
    max_upload_size: '单文件最大上传大小（字节）',
    allowed_image_types: '允许上传的图片类型（逗号分隔）',
    allowed_file_types: '允许上传的文件类型（逗号分隔）',
    use_cdn: '媒体文件启用 CDN 前缀', cdn_prefix: '媒体 CDN 地址前缀',
    watermark_text: '图片水印文字（留空则不加水印；上传时烧录到图片右下角）',
    default_title: '页面默认标题', default_description: '页面默认描述',
    default_keywords: '页面默认关键词', og_image: 'OG 分享默认图',
    twitter_handle: 'Twitter 账号', google_verification: 'Google 站点验证码',
    baidu_verification: '百度站点验证码', robots_txt: 'robots.txt 内容',
    smtp_host: 'SMTP 服务器地址', smtp_port: 'SMTP 端口',
    smtp_user: 'SMTP 用户名', smtp_password: 'SMTP 密码',
    use_tls: '启用 TLS 加密', from_address: '发件人邮箱地址',
    from_name: '发件人显示名称', enable_notifications: '启用邮件通知',
    max_login_attempts: '登录失败最大尝试次数',
    lockout_duration_sec: '登录锁定时长（秒）',
    enable_comments: '评论模块', enable_registration: '开放用户注册',
    enable_rss: 'RSS 订阅', enable_search: '站内搜索',
    enable_sitemap: '站点地图', enable_guestbook: '留言板',
    enable_dark_mode: '深色模式切换', enable_like_button: '文章点赞按钮',
    enable_share_buttons: '社交分享按钮', enable_reading_progress: '阅读进度条',
    primary_color: '主色调 Primary',
    page_width_px: '内容区最大宽度（px）',
    accent_color: '强调色 Accent', show_copyright: '显示版权声明',
    show_powered_by: '显示 Powered by 标识',
    header_style: '顶栏样式（sticky/static）', show_search: '显示搜索框',
    show_language_switch: '显示语言切换', show_theme_toggle: '显示主题切换',
    title: 'Hero 标题（多语言 JSON）',
    caption: '底部小字标语', cta_text: 'CTA 按钮文字', cta_url: 'CTA 跳转链接',
    bg_image: '背景图片 URL', bg_gradient: '背景渐变色 CSS',
    type: '公告类型（info/warning/success/error）',
    content_md: '公告正文（Markdown）', dismissible: '允许用户手动关闭',
    sticky: '滚动时仍然显示',
    text: '页脚底部文字', slogan: '站点口号标语',
    copyright: '版权声明文字', police_icp_number: '公安备案号',
    show_social_links: '显示社交链接图标', show_back_to_top: '显示回到顶部按钮'
  }[key] ?? key

  const resolvedLabel = (activeGroup.value === 'hero' && key === 'subtitle')
    ? 'Hero 副标题'
    : label

  if (value === null || value === undefined) {
    const d = defaults[key]
    if (typeof d === 'boolean') return { label: resolvedLabel, type: 'boolean' }
    if (typeof d === 'number') return { label: resolvedLabel, type: 'number' }
    return { label: resolvedLabel, type: 'string' }
  }

  if (typeof value === 'boolean') return { label: resolvedLabel, type: 'boolean' }
  if (typeof value === 'number') {
    const meta: Record<string, { min?: number, max?: number, placeholder?: string, help?: string }> = {
      posts_per_page: { min: 1, max: 50, placeholder: '1 - 50', help: '建议 10-20 之间' },
      toc_depth: { min: 1, max: 6, placeholder: '1 - 6' },
      line_height: { min: 1, max: 2.5, placeholder: '1.0 - 2.5' },
      font_size: { min: 12, max: 24, placeholder: '12 - 24' },
      max_length: { min: 100, max: 5000, placeholder: '100 - 5000' },
      max_upload_size: { min: 102400, placeholder: '单位：字节，如 10485760 = 10MB' },
      smtp_port: { min: 1, max: 65535, placeholder: '常用：465/587/25' },
      max_login_attempts: { min: 1, max: 20 },
      lockout_duration_sec: { min: 60, placeholder: '单位：秒' },
      page_width_px: { min: 800, max: 2000, placeholder: '如 1200' }
    }
    const m = meta[key] || {}
    return { label: resolvedLabel, type: 'number', ...m }
  }
  if (typeof value === 'object') {
    return { label: resolvedLabel, type: 'json', help: '数组每项应为对象，修改后需保证语法正确' }
  }
  const lowerKey = key.toLowerCase()
  if (lowerKey.includes('color')) {
    return { label: resolvedLabel, type: 'color' }
  }
  const sensitive = isSensitiveSettingKey(key)
  const longKeys = ['description', 'about_page_html', 'robots_txt', 'content_md']
  const long = longKeys.includes(key) || (typeof value === 'string' && value.length > 80)
  const help: Record<string, string> = {
    site_url: '建议包含协议前缀，如 https://example.com',
    keywords: '多个关键词之间使用英文逗号分隔',
    icp_number: '如：京ICP备XXXXXXXX号'
  }
  return { label: resolvedLabel, type: 'string', long, sensitive, help: help[key] }
}

/**
 * 去重：站点设置中与"主题 Customizer"重复的字段统一屏蔽。
 * 外观颜色 / 宽度由"主题自定义"作为唯一入口管理（useSite 里 mods 优先覆写）。
 * appearance 组里剩下的 show_copyright / show_powered_by 不与 Customizer 冲突。
 */
const APPEARANCE_BLOCK_KEYS = new Set<string>([
  'primary_color', // 主色 → 主题 Customizer（accent_color 也在 mods）
  'accent_color', // 强调色 → 主题 Customizer
  'page_width_px' // 内容区宽度 → 主题 Customizer（layout_width）
])

/**
 * hero 组里与主题 Customizer 重复的字段：
 *   - title / subtitle 文案由 theme.hero_title / hero_subtitle 管理
 *   - 仍保留 enable / caption / cta / bg 等主题 Customizer 未覆盖的交互设置
 */
const HERO_BLOCK_KEYS = new Set<string>(['title', 'subtitle'])

/**
 * footer 组里与主题 Customizer 重复的字段：
 *   - copyright → theme.footer_text 管理
 *   - 仍保留 slogan / icp / social / back_to_top 等站点级设置
 */
const FOOTER_BLOCK_KEYS = new Set<string>(['copyright'])

/**
 * reading 组里与主题 Customizer 重复的字段：
 *   - show_author_box / show_related_posts 由主题 mods 控制
 *     （reading 里的字段名可不同，但 reading 组目前不存在这些键 ——
 *      仅作防御性声明，避免后端后续加字段时前台形成双入口。）
 */
const READING_BLOCK_KEYS = new Set<string>([])

const GROUP_BLOCK_KEYS: Record<string, Set<string>> = {
  appearance: APPEARANCE_BLOCK_KEYS,
  hero: HERO_BLOCK_KEYS,
  footer: FOOTER_BLOCK_KEYS,
  reading: READING_BLOCK_KEYS
}

const currentGroupSchemas = computed(() => {
  const data = formState[activeGroup.value] || {}
  const defaults = getDefaultsFor(activeGroup.value)
  const blocks = GROUP_BLOCK_KEYS[activeGroup.value]
  const out: Record<string, FieldSchema> = {}
  for (const [k, v] of Object.entries(data)) {
    if (blocks && blocks.has(k)) continue
    out[k] = inferSchema(k, v, defaults)
  }
  return out
})

function getDefaultsFor(group: string): Record<string, SettingsValue> {
  const m: Record<string, Record<string, SettingsValue>> = {
    basic: { site_name: '', subtitle: '', logo: '', description: '', keywords: '', site_url: '', icp_number: '', about_page_html: '' },
    reading: { posts_per_page: 12, show_reading_time: true, show_word_count: true, show_toc: true, toc_depth: 3, line_height: 1.7, font_size: 16 },
    comments: { enable: true, require_approval: false, allow_guest: true, max_length: 3000, enable_antispam: true, enable_nested: true },
    media: { max_upload_size: 10485760, allowed_image_types: 'jpg,jpeg,png,gif,webp,svg', allowed_file_types: 'mp4,webm,mov,mp3,wav,ogg,pdf,doc,docx,xls,xlsx', use_cdn: false, cdn_prefix: '', watermark_text: '' },
    seo: { default_title: '', default_description: '', default_keywords: '', og_image: '', twitter_handle: '', google_verification: '', baidu_verification: '', robots_txt: '' },
    email: { smtp_host: '', smtp_port: 465, smtp_user: '', smtp_password: '', use_tls: true, from_address: '', from_name: '', enable_notifications: false },
    security: { max_login_attempts: 5, lockout_duration_sec: 1800 },
    features: { enable_comments: true, enable_registration: true, enable_rss: true, enable_search: true, enable_sitemap: true, enable_guestbook: true, enable_dark_mode: true, enable_like_button: true, enable_share_buttons: true, enable_reading_progress: true },
    appearance: { page_width_px: 1200, show_copyright: true, show_powered_by: true, primary_color: '#0EA5A9', accent_color: '#0284C7' },
    navigation: { header_style: 'sticky', show_search: true, show_language_switch: true, show_theme_toggle: true },
    hero: { enable: true, title: {}, subtitle: {}, caption: '', cta_text: {}, cta_url: '', bg_image: '', bg_gradient: '' },
    notice: { enable: false, type: 'info', title: '', content_md: '', dismissible: true, sticky: true },
    footer: { text: '', slogan: '', copyright: '', icp_number: '', police_icp_number: '', show_social_links: true, show_back_to_top: true }
  }
  return m[group] || {}
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await fetchAllSettings()
    originalState.value = JSON.parse(JSON.stringify(data))
    for (const [k, v] of Object.entries(data)) {
      formState[k] = v as SettingsGroupData
    }
  } catch (e) {
    // fetchAllSettings 内部的 apiFetch 已 toast，这里只补充可见的内联错误态（含重试）
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载站点配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSaveCurrentGroup() {
  const groupKey = activeGroup.value
  const raw = formState[groupKey]
  if (!raw) return
  saving.value = true
  try {
    // 清洗 payload，避免无意义或被禁止的字段被后端接收
    const payload: SettingsGroupData = { ...raw }
    // 去重：主题 Customizer 中已接管的字段在"站点设置"保存时强制剥离，
    // 防止"先在 Customizer 调过颜色 → 再保存站点设置 → 把主题色覆盖"的双写冲突。
    const blocks = GROUP_BLOCK_KEYS[groupKey]
    if (blocks) {
      for (const k of blocks) {
        // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
        delete payload[k]
      }
    }
    const r = await saveSettingsGroup(groupKey, payload)
    originalState.value[groupKey] = JSON.parse(JSON.stringify(r.data))
    toast.success(`已保存：${currentGroupMeta.value?.label ?? groupKey}`)
  } catch (e) {
    // saveSettingsGroup 的 apiFetch 失败时已 toast 展示后端错误；
    // 此处不再二次 toast，仅保留控制台日志便于排查
    console.error('[settings] handleSaveCurrentGroup failed:', e)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadAll()
})
</script>
