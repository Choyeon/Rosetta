<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-cyan-100 to-blue-100 dark:from-cyan-900/30 dark:to-blue-900/30 mb-5">
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
      <Card class="mb-10 overflow-hidden border-0 shadow-soft bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-900 dark:via-background dark:to-indigo-950/20">
        <CardContent class="p-8 md:p-10">
          <div class="flex flex-col md:flex-row items-center md:items-start gap-6 md:gap-8">
            <Avatar class="size-28 md:size-32 shrink-0 ring-4 ring-background shadow-xl">
              <AvatarImage src="" alt="Author" />
              <AvatarFallback class="text-3xl md:text-4xl font-display bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
                R
              </AvatarFallback>
            </Avatar>
            <div class="flex-1 text-center md:text-left">
              <div class="font-display text-2xl md:text-3xl font-bold tracking-tight mb-1">
                {{ t('about.authorName') }}
              </div>
              <div class="text-muted-foreground mb-4">{{ t('about.authorRole') }}</div>
              <div class="flex flex-wrap gap-2 justify-center md:justify-start">
                <Badge v-for="tag in profileTags" :key="tag" variant="outline" class="text-xs px-3 py-1">
                  {{ tag }}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="bio" class="w-full">
        <TabsList class="grid grid-cols-4 mb-8">
          <TabsTrigger value="bio" class="data-[state=active]:shadow-none">
            <UserCircle2 class="size-4 mr-2 hidden sm:block" />
            {{ t('about.tabBio') }}
          </TabsTrigger>
          <TabsTrigger value="skills" class="data-[state=active]:shadow-none">
            <Wrench class="size-4 mr-2 hidden sm:block" />
            {{ t('about.tabSkills') }}
          </TabsTrigger>
          <TabsTrigger value="oss" class="data-[state=active]:shadow-none">
            <GitFork class="size-4 mr-2 hidden sm:block" />
            {{ t('about.tabOSS') }}
          </TabsTrigger>
          <TabsTrigger value="contact" class="data-[state=active]:shadow-none">
            <Mail class="size-4 mr-2 hidden sm:block" />
            {{ t('about.tabContact') }}
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
                <p class="text-foreground/80 italic">{{ t('about.motto') }}</p>
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
                <Badge v-for="tech in techStack" :key="tech.name" :style="{ background: tech.bg, color: tech.color }" class="text-sm px-4 py-1.5 font-medium shadow-sm border-0">
                  {{ tech.name }}
                </Badge>
              </div>

              <div class="space-y-5">
                <div v-for="group in skillGroups" :key="group.title">
                  <div class="text-sm font-medium mb-3 text-muted-foreground flex items-center gap-2">
                    <component :is="group.icon" class="size-4" />
                    {{ group.title }}
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <Badge v-for="skill in group.items" :key="skill" variant="secondary" class="text-xs">
                      {{ skill }}
                    </Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="oss">
          <Card>
            <CardContent class="p-6 md:p-8 space-y-4">
              <a v-for="repo in ossProjects" :key="repo.name" :href="repo.url" target="_blank" rel="noopener noreferrer" class="block group rounded-xl border border-border/60 p-5 hover:shadow-soft hover:border-border transition-all duration-300">
                <div class="flex items-start justify-between gap-3 mb-2">
                  <div class="flex items-center gap-2">
                    <FolderGit2 class="size-4.5 text-primary shrink-0" />
                    <span class="font-medium group-hover:underline underline-offset-4">{{ repo.name }}</span>
                  </div>
                  <div class="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
                    <span class="inline-flex items-center gap-1">
                      <Star class="size-3.5 fill-warning text-warning" />
                      {{ repo.stars }}
                    </span>
                    <span class="inline-flex items-center gap-1">
                      <GitFork class="size-3.5" />
                      {{ repo.forks }}
                    </span>
                  </div>
                </div>
                <p class="text-sm text-muted-foreground leading-relaxed mb-3">{{ repo.desc }}</p>
                <div class="flex flex-wrap gap-1.5">
                  <Badge v-for="tag in repo.tags" :key="tag" variant="outline" class="text-[11px]">
                    {{ tag }}
                  </Badge>
                </div>
              </a>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contact">
          <Card>
            <CardContent class="p-6 md:p-8">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <a v-for="contact in contacts" :key="contact.label" :href="contact.href" target="_blank" rel="noopener noreferrer" class="flex items-center gap-4 p-4 rounded-xl border border-border/60 hover:shadow-soft hover:bg-accent/30 transition-all duration-300">
                  <div class="size-11 shrink-0 rounded-xl flex items-center justify-center" :style="{ background: contact.bg }">
                    <component :is="contact.icon" :class="['size-5', contact.color]" />
                  </div>
                  <div class="min-w-0">
                    <div class="text-xs text-muted-foreground mb-0.5">{{ contact.label }}</div>
                    <div class="font-medium truncate">{{ contact.value }}</div>
                  </div>
                </a>
              </div>

              <div class="mt-8 rounded-xl border-dashed border-2 border-border/80 p-6 bg-muted/30">
                <div class="flex items-start gap-3">
                  <Coffee class="size-5 shrink-0 text-warning mt-0.5" />
                  <div>
                    <div class="font-medium mb-1.5">{{ t('about.buyMeCoffee') }}</div>
                    <p class="text-sm text-muted-foreground leading-relaxed">{{ t('about.buyMeCoffeeDesc') }}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { useI18n } from 'vue-i18n'
import {
  User2,
  UserCircle2,
  Wrench,
  Mail,
  Quote,
  Layers,
  FolderGit2,
  Star,
  GitFork,
  Coffee,
  Globe,
  MessageSquare,
  Bird
} from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t } = useI18n()

const profileTags = computed(() => [
  t('about.tag1'),
  t('about.tag2'),
  t('about.tag3'),
  t('about.tag4')
])

const techStack = [
  { name: 'Nuxt', bg: 'linear-gradient(135deg, #00dc82, #003428)', color: '#ffffff' },
  { name: 'Vue', bg: 'linear-gradient(135deg, #42b883, #35495e)', color: '#ffffff' },
  { name: 'Tailwind', bg: 'linear-gradient(135deg, #38bdf8, #0284c7)', color: '#ffffff' },
  { name: 'Shadcn', bg: 'linear-gradient(135deg, #0f172a, #334155)', color: '#ffffff' },
  { name: 'FastAPI', bg: 'linear-gradient(135deg, #009688, #006064)', color: '#ffffff' },
  { name: 'PostgreSQL', bg: 'linear-gradient(135deg, #336791, #002a4c)', color: '#ffffff' },
  { name: 'Redis', bg: 'linear-gradient(135deg, #dc382d, #8b1e1a)', color: '#ffffff' },
  { name: 'Docker', bg: 'linear-gradient(135deg, #2496ed, #0d3b66)', color: '#ffffff' }
]

const skillGroups = [
  {
    title: 'Frontend',
    icon: Layers,
    items: ['Vue 3', 'React 18', 'TypeScript', 'Nuxt 3', 'Next.js', 'Tailwind CSS', 'Vite', 'Pinia', 'VueUse']
  },
  {
    title: 'Backend',
    icon: Wrench,
    items: ['Python / FastAPI', 'Node.js', 'Go', 'PostgreSQL', 'MySQL', 'Redis', 'SQLAlchemy', 'Prisma']
  },
  {
    title: 'DevOps',
    icon: FolderGit2,
    items: ['Docker', 'Kubernetes', 'GitHub Actions', 'Nginx', 'Linux', 'Prometheus', 'Grafana']
  },
  {
    title: 'Tools',
    icon: GitFork,
    items: ['Git', 'VSCode', 'Figma', 'Postman', 'pnpm', 'Turborepo', 'ESLint', 'Prettier']
  }
]

const ossProjects = [
  {
    name: 'rosetta-blog',
    desc: '一个为工程师与创作者打造的极简博客系统，前后端分离，多语言内置。',
    url: 'https://github.com/example/rosetta-blog',
    stars: 482,
    forks: 67,
    tags: ['Nuxt', 'Vue', 'FastAPI', 'PostgreSQL']
  },
  {
    name: 'vue-composables-kit',
    desc: '精选常用 Vue 3 组合式工具函数集，类型完备、零依赖、SSR 友好。',
    url: 'https://github.com/example/vue-composables-kit',
    stars: 231,
    forks: 18,
    tags: ['Vue 3', 'TypeScript', 'Composables']
  },
  {
    name: 'tailwind-preset-minimal',
    desc: '面向博客与文档站点的 Tailwind 预设，极客墨水配色 + 细腻排版系统。',
    url: 'https://github.com/example/tailwind-preset-minimal',
    stars: 156,
    forks: 24,
    tags: ['Tailwind', 'Design System']
  },
  {
    name: 'fastapi-template',
    desc: '生产级 FastAPI 模板：分层架构、SQLAlchemy 2.0、Docker 部署、后台任务。',
    url: 'https://github.com/example/fastapi-template',
    stars: 318,
    forks: 42,
    tags: ['FastAPI', 'PostgreSQL', 'Docker']
  }
]

const contacts = [
  {
    label: 'Email',
    value: 'hello@rosetta.dev',
    href: 'mailto:hello@rosetta.dev',
    icon: Mail,
    bg: 'linear-gradient(135deg, #dbeafe, #bfdbfe)',
    color: 'text-blue-600'
  },
  {
    label: 'GitHub',
    value: '@rosetta-dev',
    href: 'https://github.com/rosetta-dev',
    icon: GitFork,
    bg: 'linear-gradient(135deg, #f1f5f9, #cbd5e1)',
    color: 'text-slate-800'
  },
  {
    label: 'Twitter / X',
    value: '@rosetta_blog',
    href: 'https://twitter.com/rosetta_blog',
    icon: Bird,
    bg: 'linear-gradient(135deg, #e0f2fe, #bae6fd)',
    color: 'text-sky-600'
  },
  {
    label: 'Website',
    value: 'rosetta.dev',
    href: 'https://rosetta.dev',
    icon: Globe,
    bg: 'linear-gradient(135deg, #d1fae5, #a7f3d0)',
    color: 'text-emerald-600'
  },
  {
    label: 'Telegram',
    value: '@rosetta_chat',
    href: 'https://t.me/rosetta_chat',
    icon: MessageSquare,
    bg: 'linear-gradient(135deg, #cffafe, #a5f3fc)',
    color: 'text-cyan-600'
  },
  {
    label: 'RSS',
    value: '/feed.xml',
    href: '/feed.xml',
    icon: Layers,
    bg: 'linear-gradient(135deg, #ffedd5, #fed7aa)',
    color: 'text-orange-600'
  }
]
</script>
