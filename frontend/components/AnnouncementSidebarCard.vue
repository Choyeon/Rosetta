<!--
  侧栏「公告」卡：展示公告管理页维护的多条运营公告。

  契约：
  - 数据源是公开口 GET /announcements（服务端已按 is_active + 起止时间窗过滤、按 sort_order
    升序排好、缓存 60s），前端不得再判一遍可见性，也不得自己排序——口径会漂。
  - 与顶部横幅是两个表面：横幅只渲染设置页 notice 分组那一条（见 layouts/default.vue），
    这张卡渲染公告表里的多条。把多条挤进横幅会把访客要读的内容推下首屏，
    也让"站点级紧急公告"与"这一阵子的活动预告"在观感上无法区分。
  - title/content 恒为明文字符串（AnnouncementResponse 没有 link/url/target，也不是 i18n dict），
    所以这里不做链接分支、不走 v-html；但管理员写的仍是 Markdown，展示前与横幅共用
    stripInlineMarkdown 剥掉标记（两块表面各一套口径 = 同一条公告两种观感）。
  - 日期只取 ISO 串的日期段（announcementDateText）：SSR 机与访客浏览器时区不同，
    任何依赖本地时区的格式化都是首屏字节不一致的水合隐患。
  - 关闭记录与横幅共用 sessionStorage 那一份（两个来源的 id 形态互不相交，不会互相吞掉）。
-->
<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { useAPI } from '~~/composables/useApi'
import { Bell, X } from '~~/lib/lucide-svg-icons'
import {
  announcementDateText,
  announcementDotClass,
  canDismissAnnouncement,
  stripInlineMarkdown,
  useAnnouncementBar,
  type AnnouncementRow
} from '~~/composables/useAnnouncementBar'

const { t, locale } = useI18n()

const { data, pending, error } = useAPI<AnnouncementRow[]>('/announcements', {
  key: computed(() => `sidebar:announcements:${locale.value}`),
  default: () => []
})

const rows = computed<AnnouncementRow[]>(() => (Array.isArray(data.value) ? data.value : []))
const { visible, dismiss } = useAnnouncementBar(rows)

/** 后端 AnnouncementType 的四种取值；未知值落 info 文案，不渲染裸 key。 */
const TRANSLATED_TYPES = new Set(['info', 'warning', 'success', 'error'])
const typeLabel = (type?: string) =>
  t(`announcement.type_${TRANSLATED_TYPES.has(type ?? '') ? type : 'info'}`)

/** 侧栏不是公告详情页：默认只出前 5 条，其余按需展开，避免长公告把整栏撑成一屏。 */
const PREVIEW_COUNT = 5
const expanded = ref(false)
const visibleList = computed(() =>
  expanded.value ? visible.value : visible.value.slice(0, PREVIEW_COUNT)
)
const hiddenCount = computed(() => Math.max(0, visible.value.length - PREVIEW_COUNT))

/**
 * 公告的 title/content 与设置页 notice 一样是"管理员写 Markdown"的字段，但这里不是正文
 * 渲染位（不引 marked + DOMPurify、不注 HTML），所以与横幅共用 stripInlineMarkdown。
 * 各写一套的结果是同一个标记在两块表面上有两种观感：横幅上是文字，侧栏里是字面量 `**提示**`。
 */
const titleText = (ann: AnnouncementRow) => stripInlineMarkdown(ann.title)
const bodyText = (ann: AnnouncementRow) => stripInlineMarkdown(ann.content)
/** 标题与正文同源时只出一行——去重要比"去掉标记后的两份"，否则 `**公告**` 与 `公告` 会被当成两条。 */
const showsBody = (ann: AnnouncementRow) => {
  const body = bodyText(ann)
  return !!body && body !== titleText(ann)
}
</script>

<template>
  <Card>
    <CardHeader class="flex-row items-center justify-between gap-3">
      <CardTitle class="text-lg">
        <span class="inline-flex items-center gap-2">
          <Bell class="size-4 text-primary" />
          <span class="uppercase tracking-[0.16em] text-xs text-muted-foreground">
            {{ t('home.announcements') }}
          </span>
        </span>
      </CardTitle>
      <Badge
        v-if="visible.length"
        variant="secondary"
        class="rounded-full px-2 py-0 text-[11px] font-normal tabular-nums"
      >
        {{ visible.length }}
      </Badge>
    </CardHeader>
    <CardContent>
      <div
        v-if="error"
        class="text-sm text-destructive"
      >
        {{ t('error.loadFailed') }}
      </div>
      <div
        v-else-if="pending"
        class="flex flex-col gap-3"
      >
        <Skeleton
          v-for="i in 2"
          :key="i"
          class="h-14 rounded-xl"
        />
      </div>
      <ul
        v-else-if="visible.length"
        class="flex flex-col"
      >
        <li
          v-for="(ann, idx) in visibleList"
          :key="ann.id"
          :data-announcement="ann.id"
          :data-announcement-type="ann.type || 'info'"
          class="flex gap-3 py-3"
          :class="idx === 0 ? 'pt-0' : 'border-t border-border'"
        >
          <span
            :class="['mt-1 size-2 shrink-0 rounded-full', announcementDotClass(ann.type)]"
            :title="typeLabel(ann.type)"
          />
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span class="text-sm font-medium break-words">{{ titleText(ann) || typeLabel(ann.type) }}</span>
              <span
                v-if="announcementDateText(ann.created_at)"
                class="text-xs text-muted-foreground/70 tabular-nums"
              >{{ announcementDateText(ann.created_at) }}</span>
            </div>
            <p
              v-if="showsBody(ann)"
              class="mt-1 text-sm text-muted-foreground line-clamp-2 break-words"
            >
              {{ bodyText(ann) }}
            </p>
          </div>
          <button
            v-if="canDismissAnnouncement(ann)"
            type="button"
            class="shrink-0 -m-1 grid size-8 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-black/5 hover:text-foreground dark:hover:bg-white/10"
            :aria-label="t('a11y.closeAnnouncement')"
            @click="dismiss(ann.id)"
          >
            <X class="size-3.5" />
          </button>
        </li>
      </ul>
      <div
        v-else
        class="text-sm text-muted-foreground"
      >
        {{ t('announcement.none') }}
      </div>
      <button
        v-if="hiddenCount > 0"
        type="button"
        class="mt-2 text-sm text-primary transition-opacity hover:underline"
        @click="expanded = !expanded"
      >
        {{ expanded ? t('announcement.showLess') : t('announcement.showMore', { n: hiddenCount }) }}
      </button>
    </CardContent>
  </Card>
</template>
