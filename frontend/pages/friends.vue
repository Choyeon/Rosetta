<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-emerald-100 to-teal-100 dark:from-emerald-900/30 dark:to-teal-900/30 mb-5">
        <Link2 class="size-7 text-success" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('friends.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('friends.desc') }}
      </p>
    </header>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      <a
        v-for="friend in displayLinks"
        :key="friend.id"
        :href="friend.url"
        target="_blank"
        rel="noopener noreferrer"
      >
        <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden">
          <CardHeader class="p-5 pb-3">
            <div class="flex items-start gap-3 mb-3">
              <div
                class="size-12 shrink-0 rounded-xl flex items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 to-zinc-200 dark:from-slate-800 dark:to-zinc-700 transition-transform duration-300 group-hover:scale-105"
                :style="friend.bgColor ? { background: friend.bgColor } : {}"
              >
                <img v-if="friend.logo" :src="friend.logo" :alt="friend.name" class="w-full h-full object-cover" loading="lazy" />
                <span v-else class="font-display text-lg font-bold text-slate-600 dark:text-slate-300">
                  {{ friend.name?.[0]?.toUpperCase() }}
                </span>
              </div>
              <div class="flex-1 min-w-0">
                <CardTitle class="font-display text-base tracking-tight group-hover:underline underline-offset-4 truncate">
                  {{ friend.name }}
                </CardTitle>
              </div>
            </div>
            <CardDescription class="line-clamp-3 text-sm leading-relaxed min-h-[3.75rem]">
              {{ friend.description || t('friends.noDesc') }}
            </CardDescription>
          </CardHeader>
          <CardFooter class="p-5 pt-0 flex items-center justify-between text-sm border-t mt-2">
            <span class="text-muted-foreground truncate pr-2 max-w-[65%]">
              {{ friend.url?.replace(/^https?:\/\//, '') }}
            </span>
            <div class="inline-flex items-center gap-1 text-success shrink-0">
              {{ t('friends.visit') }}
              <ExternalLink class="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </div>
          </CardFooter>
        </Card>
      </a>
    </div>

    <div v-if="displayLinks.length === 0" class="text-center py-20">
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Link2 class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">{{ t('friends.noLinks') }}</h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '~~/components/ui/card'
import { useI18n } from 'vue-i18n'
import { Link2, ExternalLink } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t } = useI18n()

interface FriendLink {
  id: number
  name: string
  url: string
  logo?: string
  description?: string
  bgColor?: string
}

const defaultLinks: FriendLink[] = [
  {
    id: 1,
    name: 'Vue.js',
    url: 'https://vuejs.org',
    description: '渐进式 JavaScript 框架，易用、灵活、高效。',
    bgColor: 'linear-gradient(135deg, #42b883, #35495e)'
  },
  {
    id: 2,
    name: 'Vite',
    url: 'https://vitejs.dev',
    description: '下一代前端开发与构建工具，极速的冷启动与 HMR。',
    bgColor: 'linear-gradient(135deg, #646cff, #bd34fe)'
  },
  {
    id: 3,
    name: 'Rust',
    url: 'https://www.rust-lang.org',
    description: '赋予每个人构建可靠且高效软件的能力。',
    bgColor: 'linear-gradient(135deg, #000000, #dea584)'
  },
  {
    id: 4,
    name: 'Go',
    url: 'https://go.dev',
    description: '简单、可靠、高效的开源编程语言。',
    bgColor: 'linear-gradient(135deg, #00add8, #007d9c)'
  },
  {
    id: 5,
    name: 'Nuxt',
    url: 'https://nuxt.com',
    description: '直观的 Vue 全栈框架，构建你的下一个应用。',
    bgColor: 'linear-gradient(135deg, #00dc82, #003428)'
  },
  {
    id: 6,
    name: 'React',
    url: 'https://react.dev',
    description: '用于构建用户界面的 JavaScript 库。',
    bgColor: 'linear-gradient(135deg, #61dafb, #152238)'
  },
  {
    id: 7,
    name: 'Svelte',
    url: 'https://svelte.dev',
    description: '令人耳目一新的方式构建用户界面。',
    bgColor: 'linear-gradient(135deg, #ff3e00, #b32a00)'
  },
  {
    id: 8,
    name: 'Shadcn',
    url: 'https://ui.shadcn.com',
    description: '精美、可定制、可复制粘贴的组件集合。',
    bgColor: 'linear-gradient(135deg, #000000, #333333)'
  }
]

const links = ref<FriendLink[]>([])
const loading = ref(false)

const displayLinks = computed(() => {
  return links.value && links.value.length > 0 ? links.value : defaultLinks
})

onMounted(async () => {
  try {
    // TODO: 替换为真实 composable 调用
    // const { getFriendLinks } = useFriendLinks()
    // const result = await getFriendLinks()
    // if (result && result.length > 0) {
    //   links.value = result
    //   return
    // }

    // 真实 composable 暂未实现或返回空数据时保持默认假数据
    // links.value = []
  } catch (e) {
    console.error('[friends] fetch links error:', e)
    links.value = []
  }
})
</script>
