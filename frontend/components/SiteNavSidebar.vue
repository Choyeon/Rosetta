<!--
  侧边栏导航（lg 起，顶栏按钮 + 左侧抽屉）。

  与顶栏、移动端汉堡共用同一份导航数据：items 由 AppHeader 注入（顶栏已有
  /navigations + 兜底 + ENSURE_PRESENT 合并管线），这里不再自拉一份，避免两套
  菜单口径漂移。抽屉额外补一节「分类」——分类在顶栏只占一条入口，深链只能先
  进 /categories 再点，侧边栏把它摊平。

  分类的 useAPI 键与 AppFooter / 分类页共用 `blog:categories:<locale>`（Nuxt 按 key
  去重，同页只发一条）。抽屉里的链接只在展开时进 DOM，爬虫的链接图仍由顶栏
  SSR 输出承担，所以这里不追求 SSR 可见性。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { PanelLeft } from '~~/lib/lucide-svg-icons'
import { Button } from '~~/components/ui/button'
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose
} from '~~/components/ui/sheet'
import { Separator } from '~~/components/ui/separator'
import { isNavActive, type NavLink } from '~~/lib/navigation'
import { pickLocalizedText } from '~~/composables/useI18nHelpers'

defineProps<{ items: NavLink[] }>()

const { t, locale } = useI18n()
const route = useRoute()
const { localeHref } = useLocaleLink()

interface CategoryRow {
  id: number | string
  slug: string
  name?: string | Record<string, string>
  post_count?: number
  postsCount?: number
}

const { data: catsData } = useAPI<CategoryRow[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `blog:categories:${locale.value}`,
  default: () => []
})

// 只取前 10 条：侧边栏是速览入口，完整清单仍在 /categories
const categories = computed<CategoryRow[]>(() =>
  Array.isArray(catsData.value) ? catsData.value.slice(0, 10) : []
)
const catName = (c: CategoryRow) => pickLocalizedText(c.name, locale.value as string)
const catCount = (c: CategoryRow) => c.post_count ?? c.postsCount ?? 0
</script>

<template>
  <Sheet>
    <SheetTrigger as-child>
      <Button
        variant="ghost"
        size="icon"
        :aria-label="t('nav.sidebarNav') || 'Sidebar'"
        :title="t('nav.sidebarNav') || 'Sidebar'"
      >
        <PanelLeft />
      </Button>
    </SheetTrigger>
    <SheetContent
      side="left"
      class="w-[85%] max-w-xs flex flex-col overflow-y-auto overscroll-contain"
    >
      <SheetHeader class="text-left mb-4">
        <SheetTitle class="text-base">
          {{ t('nav.sidebarNav') || 'Sidebar' }}
        </SheetTitle>
      </SheetHeader>
      <Separator class="mb-4" />

      <nav
        class="flex flex-col gap-1"
        :aria-label="t('nav.navigation') || 'Navigation'"
      >
        <SheetClose
          v-for="item in items"
          :key="item.to"
          as-child
        >
          <NuxtLink
            :to="localeHref(item.to)"
            :target="item.target"
            :aria-current="isNavActive(route.path, item.to) ? 'page' : undefined"
            :class="[
              'px-3 py-2 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground',
              isNavActive(route.path, item.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
            ]"
          >
            {{ item.label }}
          </NuxtLink>
        </SheetClose>
      </nav>

      <template v-if="categories.length > 0">
        <Separator class="my-4" />
        <div class="px-3 mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {{ t('nav.categories') || 'Categories' }}
        </div>
        <div class="flex flex-col gap-1">
          <SheetClose
            v-for="cat in categories"
            :key="cat.id"
            as-child
          >
            <NuxtLink
              :to="localeHref(`/categories/${cat.slug}`)"
              class="flex items-center justify-between gap-2 px-3 py-1.5 text-sm rounded-md text-foreground/60 hover:bg-accent hover:text-foreground transition-colors"
            >
              <span class="truncate">{{ catName(cat) }}</span>
              <span class="shrink-0 text-xs text-muted-foreground tabular-nums">{{ catCount(cat) }}</span>
            </NuxtLink>
          </SheetClose>
        </div>
      </template>
    </SheetContent>
  </Sheet>
</template>
