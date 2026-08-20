<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div
          class="size-10 rounded-xl flex items-center justify-center"
          style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
        >
          <Settings class="size-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">
            站点设置
          </h1>
          <p class="text-sm text-muted-foreground">
            配置 Rosetta 博客系统的全部参数
          </p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <Badge
          :variant="isDirty ? 'secondary' : 'default'"
          :class="isDirty ? '' : 'bg-success-muted text-success-foreground'"
        >
          <span
            class="size-1.5 rounded-full mr-1.5"
            :class="isDirty ? 'bg-warning animate-pulse' : 'bg-success'"
          />
          {{ isDirty ? '有未保存改动' : '已保存' }}
        </Badge>
        <Button
          :disabled="!isDirty || saving"
          class="text-white"
          style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
          @click="handleSaveCurrentGroup"
        >
          <Save
            v-if="!saving"
            class="size-4"
          />
          <Loader2
            v-else
            class="size-4 animate-spin"
          />
          保存当前组
        </Button>
      </div>
    </div>

    <div
      v-if="loading"
      class="grid grid-cols-[220px_1fr] gap-6 h-[calc(100vh-220px)]"
    >
      <ScrollArea class="rounded-xl border border-border bg-card p-3">
        <div class="space-y-2">
          <Skeleton
            v-for="i in 17"
            :key="i"
            class="h-10 rounded-lg"
          />
        </div>
      </ScrollArea>
      <Card class="p-6">
        <Skeleton class="h-8 w-48 rounded mb-6" />
        <div class="space-y-4">
          <Skeleton
            v-for="i in 6"
            :key="i"
            class="h-14 rounded-lg"
          />
        </div>
      </Card>
    </div>

    <div
      v-else
      class="grid grid-cols-[220px_1fr] gap-6 h-[calc(100vh-220px)]"
    >
      <ScrollArea class="rounded-xl border border-border bg-card p-2">
        <div class="space-y-1 p-1">
          <button
            v-for="g in groups"
            :key="g.key"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left"
            :class="activeGroup === g.key
              ? 'text-white shadow-md'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
            :style="activeGroup === g.key ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
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

      <ScrollArea class="rounded-xl border border-border bg-card">
        <div class="p-6 space-y-6">
          <div class="space-y-1">
            <h2 class="text-lg font-bold">
              {{ currentGroupMeta?.label }}
            </h2>
            <p class="text-sm text-muted-foreground">
              {{ currentGroupMeta?.desc }}
            </p>
          </div>
          <Separator />
          <div class="space-y-5 max-w-3xl">
            <template
              v-for="(schema, key) in currentGroupSchemas"
              :key="key"
            >
              <template v-if="schema.type === 'string' && !schema.long && !schema.sensitive">
                <div class="space-y-2">
                  <Label class="text-sm font-medium">{{ schema.label }}</Label>
                  <Input
                    v-model="formState[activeGroup][key]"
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
                <div class="space-y-2">
                  <Label class="text-sm font-medium">{{ schema.label }}</Label>
                  <div class="relative">
                    <Input
                      v-model="formState[activeGroup][key]"
                      :type="showSensitive[key] ? 'text' : 'password'"
                      :placeholder="schema.placeholder || ''"
                      class="rounded-xl pr-11"
                    />
                    <button
                      type="button"
                      class="absolute right-2 top-1/2 -translate-y-1/2 size-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
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
                <div class="space-y-2">
                  <Label class="text-sm font-medium">{{ schema.label }}</Label>
                  <Textarea
                    v-model="formState[activeGroup][key]"
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
                <div class="space-y-2">
                  <Label class="text-sm font-medium">{{ schema.label }}</Label>
                  <Textarea
                    :model-value="stringifyJson(formState[activeGroup][key])"
                    rows="8"
                    class="rounded-xl resize-none font-mono text-xs"
                    placeholder="[]"
                    @update:model-value="parseJsonInput(key, $event)"
                  />
                  <p class="text-xs text-muted-foreground">
                    JSON 数组格式{{ schema.help ? '，' + schema.help : '' }}
                  </p>
                </div>
              </template>

              <template v-else-if="schema.type === 'number'">
                <div class="space-y-2">
                  <Label class="text-sm font-medium">{{ schema.label }}</Label>
                  <Input
                    v-model.number="formState[activeGroup][key]"
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
                  <div class="space-y-0.5">
                    <Label class="text-sm font-medium">{{ schema.label }}</Label>
                    <p
                      v-if="schema.help"
                      class="text-xs text-muted-foreground"
                    >
                      {{ schema.help }}
                    </p>
                  </div>
                  <Switch v-model="formState[activeGroup][key]" />
                </div>
              </template>

              <template v-else-if="schema.type === 'color'">
                <div class="space-y-2">
                  <Label class="text-sm font-medium">{{ schema.label }}</Label>
                  <div class="flex items-center gap-3">
                    <div class="relative">
                      <input
                        v-model="formState[activeGroup][key]"
                        type="color"
                        class="absolute inset-0 opacity-0 cursor-pointer size-11 rounded-xl"
                      >
                      <div
                        class="size-11 rounded-xl border border-border shadow-inner"
                        :style="{ background: formState[activeGroup][key] || '#ffffff' }"
                      />
                    </div>
                    <Input
                      v-model="formState[activeGroup][key]"
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
      v-if="Object.keys(formState).length === 0 && !loading"
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
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
/* Admin TS strictness bypass */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { reactive, ref, computed, watch, onMounted } from 'vue'
import {
  fetchAllSettings,
  saveSettingsGroup,
  isSensitiveSettingKey,
  type AllSettingsGroups,
  type SettingsGroupData,
  type SettingsValue
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Settings, Save, Loader2, Eye, EyeOff, AlertTriangle,
  Globe, BookOpen, MessageSquare, Image, Search, Mail, Cloud, Database,
  Shield, ToggleLeft, Palette, Menu, Link2, Sparkles, Bell, LayoutPanelLeft,
  LayoutTemplate
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Card } from '~~/components/ui/card'
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
 *  - 移除外观主题（appearance）中的 primary_color / accent_color / font_family / default_theme 等由 CSS token 统一管理的字段，
 *    避免"后台改了但 CSS 已写死"的无意义配置；
 *  - system 模式的 default_theme 已按 project_memory 规定移除，只能 light / dark。
 */
const groups = [
  { key: 'basic', label: '基础信息', icon: Globe, desc: '站点名称、副标题、描述等基础资料' },
  { key: 'reading', label: '阅读体验', icon: BookOpen, desc: '文章分页、字数统计、目录深度等' },
  { key: 'comments', label: '评论设置', icon: MessageSquare, desc: '评论开关、审核、反垃圾等' },
  { key: 'media', label: '媒体上传', icon: Image, desc: '上传大小限制、文件类型、CDN 前缀' },
  { key: 'seo', label: 'SEO 优化', icon: Search, desc: '默认标题、关键词、分析 ID 等' },
  { key: 'email', label: '邮件通知', icon: Mail, desc: 'SMTP 服务器配置、收件人设置' },
  { key: 'cdn', label: 'CDN 加速', icon: Cloud, desc: 'CDN 提供商、地址前缀、刷新 Token' },
  { key: 'cache', label: '缓存策略', icon: Database, desc: '缓存开关、TTL、自动清退规则' },
  { key: 'security', label: '安全策略', icon: Shield, desc: '会话超时、登录尝试、CORS 等' },
  { key: 'features', label: '功能开关', icon: ToggleLeft, desc: '全局功能模块开关控制' },
  { key: 'appearance', label: '外观主题', icon: Palette, desc: '代码高亮、默认主题（light/dark）、页面宽度' },
  { key: 'navigation', label: '导航菜单', icon: Menu, desc: '导航栏样式、顶栏组件开关' },
  { key: 'friendlinks', label: '友情链接', icon: Link2, desc: '友链开关、默认示例、自动审核' },
  { key: 'hero', label: '首页横幅', icon: Sparkles, desc: 'Hero 区域标题、CTA、背景图' },
  { key: 'notice', label: '站点公告', icon: Bell, desc: '公告条类型、正文、可关闭' },
  { key: 'sidebar', label: '侧边栏', icon: LayoutPanelLeft, desc: '侧边栏组件开关与排序' },
  { key: 'footer', label: '页脚', icon: LayoutTemplate, desc: '版权信息、ICP、社交链接' }
]

const activeGroup = ref('basic')
const loading = ref(true)
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
    formState[activeGroup.value][key] = []
    return
  }
  try {
    formState[activeGroup.value][key] = JSON.parse(raw)
  } catch (e) {
    toast.warning('JSON 格式有误，请检查语法')
    formState[activeGroup.value][key] = raw
  }
}

function inferSchema(key: string, value: SettingsValue, defaults: Record<string, SettingsValue>): FieldSchema {
  const label = {
    site_name: '站点名称', subtitle: '站点副标题', logo: 'Logo 图片 URL',
    description: '站点描述', keywords: 'SEO 关键词（逗号分隔）', site_url: '站点首页 URL',
    icp_number: 'ICP 备案号', about_content: '关于页面简介正文',
    posts_per_page: '每页文章数', show_reading_time: '显示预估阅读时间',
    show_word_count: '显示字数统计', show_toc: '启用文章目录',
    toc_depth: '目录最大层级深度', line_height: '正文行高（倍）',
    font_size: '正文字号（px）',
    enable: '启用评论功能', require_approval: '新评论需审核',
    allow_guest: '允许访客匿名评论', max_length: '评论最大字符数',
    enable_antispam: '启用反垃圾过滤', enable_nested: '启用嵌套回复',
    max_nested_depth: '最大嵌套层级',
    max_upload_size: '单文件最大上传大小（字节）',
    allowed_image_types: '允许上传的图片类型（逗号分隔）',
    allowed_file_types: '允许上传的文件类型（逗号分隔）',
    default_post_cover: '文章默认封面图 URL',
    default_avatar: '用户默认头像 URL',
    use_cdn: '媒体文件启用 CDN 前缀', cdn_prefix: '媒体 CDN 地址前缀',
    default_title: '页面默认标题', default_description: '页面默认描述',
    default_keywords: '页面默认关键词', og_image: 'OG 分享默认图',
    twitter_handle: 'Twitter 账号', google_analytics_id: 'Google Analytics ID',
    baidu_analytics_id: '百度统计 ID', google_verification: 'Google 站点验证码',
    baidu_verification: '百度站点验证码', robots_txt: 'robots.txt 内容',
    smtp_host: 'SMTP 服务器地址', smtp_port: 'SMTP 端口',
    smtp_user: 'SMTP 用户名', smtp_password: 'SMTP 密码',
    use_tls: '启用 TLS 加密', from_address: '发件人邮箱地址',
    from_name: '发件人显示名称', enable_notifications: '启用邮件通知',
    admin_email: '管理员收件邮箱',
    provider: 'CDN 服务提供商', cdn_url: '全站 CDN 前缀',
    image_cdn_url: '图片专用 CDN 前缀', static_cdn_url: '静态资源 CDN 前缀',
    purge_token: 'CDN 刷新 Token',
    backend: '缓存后端（memory/redis）', default_ttl: '默认缓存 TTL（秒）',
    site_config_ttl: '站点配置缓存 TTL（秒）', post_list_ttl: '文章列表缓存 TTL（秒）',
    flush_on_post_update: '文章更新时自动清退相关缓存',
    require_email_verification: '用户注册需邮箱验证',
    allow_password_reset: '允许用户自助重置密码',
    session_timeout_sec: '会话超时时间（秒）',
    max_login_attempts: '登录失败最大尝试次数',
    lockout_duration_sec: '登录锁定时长（秒）',
    enable_rate_limit: '启用 API 频率限制',
    allowed_hosts: '允许的 Host（逗号分隔，* 为全部）',
    cors_origins: 'CORS 允许来源（逗号分隔）',
    enable_comments: '评论模块', enable_registration: '开放用户注册',
    enable_rss: 'RSS 订阅', enable_search: '站内搜索',
    enable_sitemap: '站点地图', enable_guestbook: '留言板',
    enable_dark_mode: '深色模式切换', enable_like_button: '文章点赞按钮',
    enable_share_buttons: '社交分享按钮', enable_reading_progress: '阅读进度条',
    code_theme: '浅色代码主题', code_theme_dark: '深色代码主题',
    default_theme: '默认主题（system/light/dark）',
    primary_color: '主色调 Primary', font_family: '正文字体族',
    page_width_px: '内容区最大宽度（px）',
    accent_color: '强调色 Accent', show_copyright: '显示版权声明',
    show_powered_by: '显示 Powered by 标识',
    header_style: '顶栏样式（sticky/static）', show_search: '显示搜索框',
    show_language_switch: '显示语言切换', show_theme_toggle: '显示主题切换',
    custom_links: '自定义链接（JSON 数组）',
    links: '推荐友情链接（JSON 数组）', auto_approve: '自动审核通过申请',
    title: 'Hero 标题（多语言 JSON）', subtitle: 'Hero 副标题',
    caption: '底部小字标语', cta_text: 'CTA 按钮文字', cta_url: 'CTA 跳转链接',
    bg_image: '背景图片 URL', bg_gradient: '背景渐变色 CSS',
    type: '公告类型（info/warning/success/error）',
    content_md: '公告正文（Markdown）', dismissible: '允许用户手动关闭',
    sticky: '滚动时仍然显示',
    show_profile: '显示博主资料卡', show_categories: '显示分类列表',
    show_tags: '显示标签列表', show_recent_posts: '显示近期文章',
    show_recent_comments: '显示最新评论', show_tag_cloud: '显示标签云',
    show_site_info: '显示站点统计', show_music: '显示音乐播放器',
    show_statistics: '显示数据统计', show_dynamics: '显示动态说说',
    widget_order: '组件排序（JSON 数组）',
    text: '页脚底部文字', slogan: '站点口号标语',
    copyright: '版权声明文字', police_icp_number: '公安备案号',
    show_social_links: '显示社交链接图标', show_back_to_top: '显示回到顶部按钮'
  }[key] ?? key

  if (value === null || value === undefined) {
    const d = defaults[key]
    if (typeof d === 'boolean') return { label, type: 'boolean' }
    if (typeof d === 'number') return { label, type: 'number' }
    return { label, type: 'string' }
  }

  if (typeof value === 'boolean') return { label, type: 'boolean' }
  if (typeof value === 'number') {
    const meta: Record<string, { min?: number, max?: number, placeholder?: string, help?: string }> = {
      posts_per_page: { min: 1, max: 50, placeholder: '1 - 50', help: '建议 10-20 之间' },
      toc_depth: { min: 1, max: 6, placeholder: '1 - 6' },
      line_height: { min: 1, max: 2.5, placeholder: '1.0 - 2.5' },
      font_size: { min: 12, max: 24, placeholder: '12 - 24' },
      max_length: { min: 100, max: 5000, placeholder: '100 - 5000' },
      max_nested_depth: { min: 1, max: 8, placeholder: '1 - 8' },
      max_upload_size: { min: 102400, placeholder: '单位：字节，如 10485760 = 10MB' },
      smtp_port: { min: 1, max: 65535, placeholder: '常用：465/587/25' },
      default_ttl: { min: 60, placeholder: '单位：秒' },
      site_config_ttl: { min: 60, placeholder: '单位：秒' },
      post_list_ttl: { min: 30, placeholder: '单位：秒' },
      session_timeout_sec: { min: 300, placeholder: '单位：秒，如 3600 = 1h' },
      max_login_attempts: { min: 1, max: 20 },
      lockout_duration_sec: { min: 60, placeholder: '单位：秒' },
      page_width_px: { min: 800, max: 2000, placeholder: '如 1200' }
    }
    const m = meta[key] || {}
    return { label, type: 'number', ...m }
  }
  if (typeof value === 'object') {
    return { label, type: 'json', help: '数组每项应为对象，修改后需保证语法正确' }
  }
  const lowerKey = key.toLowerCase()
  if (lowerKey.includes('color')) {
    return { label, type: 'color' }
  }
  const sensitive = isSensitiveSettingKey(key)
  const longKeys = ['description', 'about_content', 'robots_txt', 'content_md', 'custom_links', 'widget_order', 'links']
  const long = longKeys.includes(key) || (typeof value === 'string' && value.length > 80)
  const help: Record<string, string> = {
    site_url: '建议包含协议前缀，如 https://example.com',
    keywords: '多个关键词之间使用英文逗号分隔',
    allowed_hosts: '* 代表允许所有 Host；多个域名逗号分隔',
    cors_origins: '* 代表允许任意来源；多个来源逗号分隔',
    icp_number: '如：京ICP备XXXXXXXX号',
    default_theme: '仅支持 light / dark；为避免前后台切换主题黑屏，不再提供 system 跟随系统'
  }
  return { label, type: 'string', long, sensitive, help: help[key] }
}

/**
 * 在 appearance 组中被 CSS token 统一管理、因此不允许用户在后台修改的字段。
 * 说明：
 *   - primary_color / accent_color 不再屏蔽 —— 前端已实现
 *     `theme_primary` / `theme_accent` 动态注入 CSS 变量，
 *     后台修改后立即影响全站主色/强调色，是"站点设置"核心能力。
 */
const APPEARANCE_BLOCK_KEYS = new Set([
  'font_family'  // 字体族由 Tailwind preset（@theme/typography）管理
])

/** default_theme 允许的值（不再支持 system） */
const ALLOWED_DEFAULT_THEMES = new Set(['light', 'dark'])

const currentGroupSchemas = computed(() => {
  const data = formState[activeGroup.value] || {}
  const defaults = getDefaultsFor(activeGroup.value)
  const out: Record<string, FieldSchema> = {}
  for (const [k, v] of Object.entries(data)) {
    if (activeGroup.value === 'appearance' && APPEARANCE_BLOCK_KEYS.has(k)) continue
    out[k] = inferSchema(k, v, defaults)
  }
  return out
})

function getDefaultsFor(group: string): Record<string, SettingsValue> {
  const m: Record<string, Record<string, SettingsValue>> = {
    basic: { site_name: '', subtitle: '', logo: '', description: '', keywords: '', site_url: '', icp_number: '', about_content: '' },
    reading: { posts_per_page: 12, show_reading_time: true, show_word_count: true, show_toc: true, toc_depth: 3, line_height: 1.7, font_size: 16 },
    comments: { enable: true, require_approval: false, allow_guest: false, max_length: 1000, enable_antispam: true, enable_nested: true, max_nested_depth: 3 },
    media: { max_upload_size: 10485760, allowed_image_types: '', allowed_file_types: '', default_post_cover: '', default_avatar: '', use_cdn: false, cdn_prefix: '' },
    seo: { default_title: '', default_description: '', default_keywords: '', og_image: '', twitter_handle: '', google_analytics_id: '', baidu_analytics_id: '', google_verification: '', baidu_verification: '', robots_txt: '' },
    email: { smtp_host: '', smtp_port: 465, smtp_user: '', smtp_password: '', use_tls: true, from_address: '', from_name: '', enable_notifications: false, admin_email: '' },
    cdn: { enable: false, provider: '', cdn_url: '', image_cdn_url: '', static_cdn_url: '', purge_token: '' },
    cache: { enable: true, backend: 'memory', default_ttl: 3600, site_config_ttl: 3600, post_list_ttl: 600, flush_on_post_update: true },
    security: { require_email_verification: false, allow_password_reset: true, session_timeout_sec: 3600, max_login_attempts: 5, lockout_duration_sec: 1800, enable_rate_limit: true, allowed_hosts: '*', cors_origins: '*' },
    features: { enable_comments: true, enable_registration: true, enable_rss: true, enable_search: true, enable_sitemap: true, enable_guestbook: true, enable_dark_mode: true, enable_like_button: true, enable_share_buttons: true, enable_reading_progress: true },
    appearance: { code_theme: '', code_theme_dark: '', default_theme: 'light', page_width_px: 1200, show_copyright: true, show_powered_by: true, primary_color: '#0EA5A9', accent_color: '#0284C7' },
    navigation: { header_style: 'sticky', show_search: true, show_language_switch: true, show_theme_toggle: true, custom_links: [] },
    friendlinks: { enable: true, links: [], auto_approve: false },
    hero: { enable: true, title: {}, subtitle: {}, caption: '', cta_text: {}, cta_url: '', bg_image: '', bg_gradient: '' },
    notice: { enable: false, type: 'info', title: '', content_md: '', dismissible: true, sticky: true },
    sidebar: { show_profile: true, show_categories: true, show_tags: true, show_recent_posts: true, show_recent_comments: true, show_tag_cloud: true, show_site_info: true, show_music: true, show_statistics: true, show_dynamics: true, widget_order: [] },
    footer: { text: '', slogan: '', copyright: '', icp_number: '', police_icp_number: '', show_social_links: true, show_back_to_top: true }
  }
  return m[group] || {}
}

async function loadAll() {
  loading.value = true
  try {
    const data = await fetchAllSettings()
    originalState.value = JSON.parse(JSON.stringify(data))
    for (const [k, v] of Object.entries(data)) {
      formState[k] = v as SettingsGroupData
    }
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAllSettings'}`)
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
    if (groupKey === 'appearance') {
      for (const k of APPEARANCE_BLOCK_KEYS) delete payload[k]
      if (typeof payload.default_theme === 'string') {
        payload.default_theme = ALLOWED_DEFAULT_THEMES.has(payload.default_theme)
          ? payload.default_theme
          : 'light'
      }
    }
    const r = await saveSettingsGroup(groupKey, payload)
    originalState.value[groupKey] = JSON.parse(JSON.stringify(r.data))
    toast.success(`已保存：${currentGroupMeta.value?.label ?? groupKey}`)
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'saveSettingsGroup'}`)
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>
