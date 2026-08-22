<template>
  <div class="container py-16">
    <!-- HTML 模式：管理员在站点设置 basic.about_page_html 以 HTML 方式直接编辑关于内容 -->
    <section
      v-if="aboutPageHtml"
      class="max-w-4xl mx-auto prose prose-sky dark:prose-invert max-w-none prose-img:rounded-xl prose-headings:font-display"
      v-html="aboutPageHtml"
    />

    <!-- 回退模式：about_page_html 留空时展示默认 Tabs 结构 -->
    <template v-else>
      <header class="mb-12 text-center max-w-2xl mx-auto">
        <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
          <User2 class="size-7 text-primary" />
        </div>
        <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
          {{ t('about.title') }}
        </h1>
        <p class="text-muted-foreground mt-3 leading-relaxed">
          {{ t('about.desc') }}
        </p>
      </header>

      <div class="max-w-4xl mx-auto">
        <Card class="mb-10 overflow-hidden border-0 shadow-soft bg-gradient-to-br from-slate-50 via-white to-primary/5 dark:from-slate-900 dark:via-background dark:to-primary/10">
          <CardContent class="p-8 md:p-10">
            <div class="flex flex-col md:flex-row items-center md:items-start gap-6 md:gap-8">
              <Avatar class="size-28 md:size-32 shrink-0 ring-4 ring-background shadow-xl">
                <AvatarImage
                  :src="avatarUrl || ''"
                  alt="Author"
                />
                <AvatarFallback class="text-3xl md:text-4xl font-display bg-gradient-to-br from-primary to-accent text-white">
                  {{ authorInitial }}
                </AvatarFallback>
              </Avatar>
              <div class="flex-1 text-center md:text-left">
                <div class="font-display text-2xl md:text-3xl font-bold tracking-tight mb-1">
                  {{ authorName }}
                </div>
                <div class="text-muted-foreground mb-4">
                  {{ siteDescription }}
                </div>
                <div class="flex flex-wrap gap-2 justify-center md:justify-start">
                  <Badge
                    v-for="tag in profileTags"
                    :key="tag"
                    variant="outline"
                    class="text-xs px-3 py-1"
                  >
                    {{ tag }}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs
          default-value="bio"
          class="w-full"
        >
          <TabsList class="grid grid-cols-3 sm:grid-cols-4 mb-8">
            <TabsTrigger
              value="bio"
              class="data-[state=active]:shadow-none"
            >
              <UserCircle2 class="size-4 mr-2 hidden sm:block" />
              {{ t('about.tabBio') }}
            </TabsTrigger>
            <TabsTrigger
              value="skills"
              class="data-[state=active]:shadow-none"
            >
              <Wrench class="size-4 mr-2 hidden sm:block" />
              {{ t('about.tabSkills') }}
            </TabsTrigger>
            <TabsTrigger
              value="contact"
              class="data-[state=active]:shadow-none"
            >
              <Mail class="size-4 mr-2 hidden sm:block" />
              {{ t('about.tabContact') }}
            </TabsTrigger>
            <TabsTrigger
              value="rss"
              class="data-[state=active]:shadow-none"
            >
              <Rss class="size-4 mr-2 hidden sm:block" />
              {{ t('about.tabRss') || '订阅' }}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="bio">
            <Card>
              <CardContent class="p-6 md:p-8 space-y-5 text-foreground/90 leading-relaxed">
                <p>{{ t('about.bioP1') }}</p>
                <p>{{ t('about.bioP2') }}</p>
                <p>{{ t('about.bioP3') }}</p>
                <div class="rounded-xl border-dashed border-2 border-border/80 p-5 bg-muted/30 mt-6">
                  <div class="font-medium mb-2 flex items-center gap-2">
                    <Quote class="size-4 text-primary" />
                    {{ t('about.mottoLabel') }}
                  </div>
                  <p class="text-foreground/80 italic">
                    {{ t('about.motto') }}
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="skills">
            <Card>
              <CardHeader class="pb-4">
                <CardTitle class="text-lg flex items-center gap-2">
                  <Layers class="size-4 text-primary" />
                  {{ t('about.techStack') }}
                </CardTitle>
                <CardDescription>{{ t('about.techStackDesc') }}</CardDescription>
              </CardHeader>
              <CardContent class="pt-0">
                <div class="flex flex-wrap gap-2 mb-8">
                  <Badge
                    v-for="tech in techStack"
                    :key="tech.name"
                    :style="{ background: tech.bg, color: tech.color }"
                    class="text-sm px-4 py-1.5 font-medium shadow-sm border-0"
                  >
                    {{ tech.name }}
                  </Badge>
                </div>

                <div class="space-y-5">
                  <div
                    v-for="group in skillGroups"
                    :key="group.title"
                  >
                    <div class="text-sm font-medium mb-3 text-muted-foreground flex items-center gap-2">
                      <component
                        :is="group.icon"
                        class="size-4"
                      />
                      {{ group.title }}
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <Badge
                        v-for="skill in group.items"
                        :key="skill"
                        variant="secondary"
                        class="text-xs"
                      >
                        {{ skill }}
                      </Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="contact">
            <Card>
              <CardContent class="p-6 md:p-8">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <a
                    v-for="contact in contacts"
                    :key="contact.label"
                    :href="contact.href"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center gap-4 p-4 rounded-xl border border-border/60 hover:shadow-soft hover:bg-accent/30 transition-all duration-300"
                  >
                    <div
                      class="size-11 shrink-0 rounded-xl flex items-center justify-center bg-primary/10"
                    >
                      <component
                        :is="contact.icon"
                        class="size-5 text-primary"
                      />
                    </div>
                    <div class="min-w-0">
                      <div class="text-xs text-muted-foreground mb-0.5">{{ contact.label }}</div>
                      <div class="font-medium truncate">{{ contact.value }}</div>
                    </div>
                  </a>
                </div>

                <div
                  v-if="contacts.length === 0"
                  class="text-center py-8 text-muted-foreground"
                >
                  {{ t('about.noContacts') || '管理员暂未公开联系方式。' }}
                </div>

                <div class="mt-8 rounded-xl border-dashed border-2 border-border/80 p-6 bg-muted/30">
                  <div class="flex items-start gap-3">
                    <Coffee class="size-5 shrink-0 text-warning mt-0.5" />
                    <div>
                      <div class="font-medium mb-1.5">
                        {{ t('about.buyMeCoffee') }}
                      </div>
                      <p class="text-sm text-muted-foreground leading-relaxed">
                        {{ t('about.buyMeCoffeeDesc') }}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="rss">
            <Card>
              <CardContent class="p-6 md:p-8 space-y-4">
                <div class="rounded-xl border border-border/60 p-5">
                  <div class="flex items-center justify-between flex-wrap gap-3">
                    <div class="flex items-center gap-3">
                      <div class="size-11 shrink-0 rounded-xl flex items-center justify-center bg-orange-100 dark:bg-orange-950/40">
                        <Rss class="size-5 text-orange-600 dark:text-orange-400" />
                      </div>
                      <div>
                        <div class="font-medium">
                          {{ t('about.rssFeed') || 'RSS 订阅' }}
                        </div>
                        <div class="text-xs text-muted-foreground break-all">
                          /rss.xml
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      @click="navigateTo('/rss.xml', { external: true })"
                    >
                      <ExternalLink class="size-3.5 mr-2" />
                      {{ t('common.open') || '打开' }}
                    </Button>
                  </div>
                </div>
                <div class="rounded-xl border border-border/60 p-5">
                  <div class="flex items-center justify-between flex-wrap gap-3">
                    <div class="flex items-center gap-3">
                      <div class="size-11 shrink-0 rounded-xl flex items-center justify-center bg-emerald-100 dark:bg-emerald-950/40">
                        <Map class="size-5 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <div>
                        <div class="font-medium">
                          {{ t('about.sitemap') || '站点地图 Sitemap' }}
                        </div>
                        <div class="text-xs text-muted-foreground break-all">
                          /sitemap.xml
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      @click="navigateTo('/sitemap.xml', { external: true })"
                    >
                      <ExternalLink class="size-3.5 mr-2" />
                      {{ t('common.open') || '打开' }}
                    </Button>
                  </div>
                </div>
                <p class="text-sm text-muted-foreground leading-relaxed pt-2">
                  {{ t('about.rssHint') || '通过 RSS 或站点地图，可以及时获取最新文章更新，或被搜索引擎正常收录。' }}
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Button } from '~~/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { useI18n } from 'vue-i18n'
import type { Component } from 'vue'
import {
  User2,
  UserCircle2,
  Wrench,
  Mail,
  Quote,
  Layers,
  Coffee,
  Rss,
  Map,
  ExternalLink,
  Globe
} from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t } = useI18n()

// 全站统一的站点配置：layouts/default.vue 里已经 await useSite().ensureLoaded()，
// 这里直接消费 useSite()，不再重复发起 useAPI('/config')，保证品牌名/logo/关于 HTML 等
// 与 AppHeader、Footer 读取的是同一份数据，避免不同组件各拉一份配置产生差异。
const site = useSite()

// 关于页 HTML 正文：admin 在站点设置 basic.about_page_html 直接写 HTML，
// 有内容时走 v-html 渲染（完整自定义内容），为空时回退默认 i18n Tabs 结构。
const aboutPageHtml = computed(() => String(site.basic.value.about_page_html || '').trim())

// useHead：页面标题/描述统一走 useSite.withSuffix / basic.* 真实数据
useHead(() => ({
  title: site.withSuffix(t('about.title') as string || '关于'),
  meta: [
    { name: 'description', content: site.basic.value.description || t('about.desc') as string },
    { name: 'keywords', content: site.basic.value.keywords }
  ]
}))

interface SiteConfigLite {
  site_name: string
  site_description: string
  site_author: string
  site_email: string
  site_logo?: string | null
  site_icon?: string | null
  site_favicon?: string | null
  contact_email?: string | null
  contact_qq?: string | null
  contact_wechat?: string | null
  github_url?: string | null
  x_url?: string | null
  bilibili_url?: string | null
  weibo_url?: string | null
  zhihu_url?: string | null
  youtube_url?: string | null
  linkedin_url?: string | null
  telegram_url?: string | null
}

const config = computed<SiteConfigLite>(() => {
  const p = site.state.value.publicConfig as Record<string, unknown> | null
  const data = (p && typeof p === 'object' ? p : {}) as unknown as SiteConfigLite
  return {
    site_name: data.site_name || site.basic.value.site_name,
    site_description: data.site_description || site.basic.value.description,
    site_author: data.site_author || site.basic.value.site_name,
    site_email: data.site_email || '',
    site_logo: data.site_logo || site.basic.value.logo || null,
    site_icon: data.site_icon || null,
    site_favicon: data.site_favicon || null,
    contact_email: data.contact_email || data.site_email || null,
    contact_qq: data.contact_qq || null,
    contact_wechat: data.contact_wechat || null,
    github_url: data.github_url || null,
    x_url: data.x_url || null,
    bilibili_url: data.bilibili_url || null,
    weibo_url: data.weibo_url || null,
    zhihu_url: data.zhihu_url || null,
    youtube_url: data.youtube_url || null,
    linkedin_url: data.linkedin_url || null,
    telegram_url: data.telegram_url || null
  }
})

const authorName = computed(() => {
  const author = config.value.site_author || config.value.site_name || (t('about.authorName') as string)
  return author || 'Author'
})

const authorInitial = computed(() => {
  const name = String(authorName.value || 'R').trim()
  return name.slice(0, 1).toUpperCase()
})

const avatarUrl = computed(() => {
  return config.value.site_logo || config.value.site_icon || ''
})

const siteDescription = computed(() => {
  const d = config.value.site_description
  if (d) return d
  return t('about.authorRole') as string
})

const profileTags = computed(() => {
  const base: string[] = []
  const tryAdd = (val: string | null | undefined | false) => {
    const s = typeof val === 'string' ? val.trim() : ''
    if (s) base.push(s)
  }
  // 若后端未配置个人标签，则回退到 i18n 中的默认 tag
  tryAdd(t('about.tag1') as string)
  tryAdd(t('about.tag2') as string)
  tryAdd(t('about.tag3') as string)
  tryAdd(t('about.tag4') as string)
  // 去重
  return Array.from(new Set(base)).slice(0, 6)
})

// 技术栈与技能组：后端暂无专门返回该类数据的 API，
// 为避免编造"个人履历"，这里严格不写死任何示例项。
// 后续如果 settings 组增加 "about_tech_stack" 字段，可直接接入。
interface TechChip { name: string, bg?: string, color?: string }
interface SkillGroupItem { title: string, items: string[], icon?: Component }

const techStack: TechChip[] = []
const skillGroups: SkillGroupItem[] = []

interface ContactItem {
  label: string
  value: string
  href: string
  icon: Component
}

const contacts = computed<ContactItem[]>(() => {
  const cfg = config.value
  const list: ContactItem[] = []
  if (cfg.contact_email || cfg.site_email) {
    const value = cfg.contact_email || cfg.site_email || ''
    list.push({
      label: 'Email',
      value,
      href: `mailto:${value}`,
      icon: Mail
    })
  }
  if (cfg.github_url) {
    let display = cfg.github_url
    try {
      display = new URL(cfg.github_url).host + new URL(cfg.github_url).pathname
    } catch {
      /* ignore */
    }
    list.push({ label: 'GitHub', value: display, href: cfg.github_url, icon: ExternalLink })
  }
  if (cfg.x_url) {
    let display = cfg.x_url
    try {
      display = new URL(cfg.x_url).host + new URL(cfg.x_url).pathname
    } catch {
      /* ignore */
    }
    list.push({ label: 'X / Twitter', value: display, href: cfg.x_url, icon: Globe })
  }
  if (cfg.telegram_url) {
    let display = cfg.telegram_url
    try {
      display = new URL(cfg.telegram_url).pathname.replace(/^\//, '') || display
    } catch {
      /* ignore */
    }
    list.push({ label: 'Telegram', value: display, href: cfg.telegram_url, icon: Globe })
  }
  if (cfg.bilibili_url) {
    let display = cfg.bilibili_url
    try {
      display = new URL(cfg.bilibili_url).host + new URL(cfg.bilibili_url).pathname
    } catch {
      /* ignore */
    }
    list.push({ label: 'Bilibili', value: display, href: cfg.bilibili_url, icon: Globe })
  }
  if (cfg.weibo_url) {
    let display = cfg.weibo_url
    try {
      display = new URL(cfg.weibo_url).host + new URL(cfg.weibo_url).pathname
    } catch {
      /* ignore */
    }
    list.push({ label: 'Weibo', value: display, href: cfg.weibo_url, icon: Globe })
  }
  if (cfg.zhihu_url) {
    let display = cfg.zhihu_url
    try {
      display = new URL(cfg.zhihu_url).host + new URL(cfg.zhihu_url).pathname
    } catch {
      /* ignore */
    }
    list.push({ label: 'Zhihu', value: display, href: cfg.zhihu_url, icon: Globe })
  }
  if (cfg.youtube_url) {
    let display = cfg.youtube_url
    try {
      display = new URL(cfg.youtube_url).host + new URL(cfg.youtube_url).pathname
    } catch {
      /* ignore */
    }
    list.push({ label: 'YouTube', value: display, href: cfg.youtube_url, icon: Globe })
  }
  if (cfg.linkedin_url) {
    let display = cfg.linkedin_url
    try {
      display = new URL(cfg.linkedin_url).host + new URL(cfg.linkedin_url).pathname
    } catch {
      /* ignore */
    }
    list.push({ label: 'LinkedIn', value: display, href: cfg.linkedin_url, icon: Globe })
  }
  return list
})
</script>
