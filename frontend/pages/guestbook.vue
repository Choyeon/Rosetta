<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-slate-100 to-zinc-200 dark:from-slate-900/30 dark:to-zinc-800/40 mb-5">
        <MessageSquare class="size-7 text-slate-700 dark:text-slate-300" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('guestbook.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('guestbook.desc') }}
      </p>
    </header>

    <Card class="mb-12 border-dashed">
      <CardHeader class="pb-4">
        <CardTitle class="text-lg flex items-center gap-2">
          <PenLine class="size-4 text-muted-foreground" />
          {{ t('guestbook.writeMessage') }}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <Input v-model="form.nickname" :placeholder="t('guestbook.nickname')" />
          <Input v-model="form.email" type="email" :placeholder="t('guestbook.email')" />
          <Input v-model="form.website" :placeholder="t('guestbook.website')" />
        </div>
        <Textarea v-model="form.content" :placeholder="t('guestbook.contentPlaceholder')" rows="4" class="resize-none mb-4" />
        <div class="flex justify-end">
          <Button @click="submitGuestbook">
            <Send class="size-4 mr-2" />
            {{ t('common.submit') }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <div class="space-y-6">
      <div v-for="item in guestbookList" :key="item.id" class="relative">
        <Card class="transition-all hover:shadow-soft duration-300">
          <CardContent class="p-6">
            <div class="flex gap-4">
              <Avatar class="size-10 shrink-0">
                <AvatarImage :src="item.avatar ?? ''" :alt="item.nickname ?? ''" />
                <AvatarFallback>{{ item.nickname?.[0]?.toUpperCase() || 'G' }}</AvatarFallback>
              </Avatar>
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap items-center gap-2 mb-1">
                  <span class="font-medium">{{ item.nickname }}</span>
                  <a v-if="item.website" :href="item.website" target="_blank" rel="noopener noreferrer" class="text-xs text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]">
                    {{ item.website.replace(/^https?:\/\//, '') }}
                  </a>
                  <span class="text-xs text-muted-foreground">{{ formatDate(item.createdAt) }}</span>
                </div>
                <p class="text-foreground/90 leading-relaxed whitespace-pre-wrap">{{ item.content }}</p>
                <div class="flex items-center gap-4 mt-3">
                  <button class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors" @click="toggleLike(item)">
                    <Heart :class="['size-4', item.liked ? 'fill-error text-error' : '']" />
                    <span>{{ item.likesCount || 0 }}</span>
                  </button>
                  <button class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors" @click="toggleReplyInput(item)">
                    <MessageCircle class="size-4" />
                    <span>{{ t('comment.reply') }}</span>
                  </button>
                </div>

                <div v-if="replyOpenId === item.id" class="mt-4 space-y-3 p-4 rounded-xl bg-muted/40 border border-border/50">
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <Input v-model="replyForm.nickname" :placeholder="t('guestbook.nickname')" size="sm" />
                    <Input v-model="replyForm.email" type="email" :placeholder="t('guestbook.email')" size="sm" />
                    <Input v-model="replyForm.website" :placeholder="t('guestbook.website')" size="sm" />
                  </div>
                  <Textarea v-model="replyForm.content" :placeholder="t('guestbook.replyPlaceholder')" rows="2" class="resize-none" />
                  <div class="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" @click="replyOpenId = null">{{ t('common.cancel') }}</Button>
                    <Button size="sm" @click="submitReply(item)">
                      <Send class="size-3.5 mr-2" />
                      {{ t('comment.reply') }}
                    </Button>
                  </div>
                </div>

                <div v-if="item.replies?.length" class="mt-4 space-y-4 pl-4 border-l-2 border-border/60">
                  <div v-for="reply in item.replies" :key="reply.id" class="flex gap-3">
                    <Avatar class="size-8 shrink-0">
                      <AvatarImage :src="reply.avatar ?? ''" :alt="reply.nickname ?? ''" />
                      <AvatarFallback class="text-xs">{{ reply.nickname?.[0]?.toUpperCase() || 'R' }}</AvatarFallback>
                    </Avatar>
                    <div class="flex-1 min-w-0">
                      <div class="flex flex-wrap items-center gap-2 mb-1">
                        <span class="font-medium text-sm">{{ reply.nickname }}</span>
                        <a v-if="reply.website" :href="reply.website" target="_blank" rel="noopener noreferrer" class="text-xs text-muted-foreground hover:text-foreground transition-colors truncate max-w-[160px]">
                          {{ reply.website.replace(/^https?:\/\//, '') }}
                        </a>
                        <span class="text-xs text-muted-foreground">{{ formatDate(reply.createdAt) }}</span>
                      </div>
                      <p class="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">{{ reply.content }}</p>
                      <div class="flex items-center gap-4 mt-2">
                        <button class="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors" @click="toggleReplyLike(reply)">
                          <Heart :class="['size-3.5', reply.liked ? 'fill-error text-error' : '']" />
                          <span>{{ reply.likesCount || 0 }}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <div v-if="guestbookList.length === 0" class="text-center py-20">
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <MessageSquare class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">{{ t('guestbook.noMessages') }}</h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { useI18n } from 'vue-i18n'
import { MessageSquare, PenLine, Send, Heart, MessageCircle } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t } = useI18n()

// TODO: 替换为真实 composable
// const { guestbookList, loading, fetchGuestbook, submitGuestbook: submitGB } = useGuestbook()

const form = reactive({
  nickname: '',
  email: '',
  website: '',
  content: ''
})

const replyForm = reactive({
  nickname: '',
  email: '',
  website: '',
  content: ''
})

const replyOpenId = ref<number | null>(null)

interface ReplyItem {
  id: number
  nickname: string
  email?: string
  website?: string
  avatar?: string
  content: string
  createdAt: string
  likesCount: number
  liked?: boolean
}

interface GuestbookItem {
  id: number
  nickname: string
  email?: string
  website?: string
  avatar?: string
  content: string
  createdAt: string
  likesCount: number
  liked?: boolean
  replies?: ReplyItem[]
}

const guestbookList = ref<GuestbookItem[]>([
  {
    id: 1,
    nickname: '林清远',
    email: 'lin@example.com',
    website: 'https://linqingyuan.dev',
    avatar: '',
    content: '博客风格真不错，极简的设计让阅读体验非常舒服。最近也在折腾自己的小站，有空来串门呀～',
    createdAt: new Date(Date.now() - 3600000 * 2).toISOString(),
    likesCount: 12,
    liked: false,
    replies: [
      {
        id: 101,
        nickname: 'Rosetta',
        website: 'https://rosetta.dev',
        avatar: '',
        content: '感谢支持！常来常往 👋',
        createdAt: new Date(Date.now() - 3600000 * 1.5).toISOString(),
        likesCount: 3
      }
    ]
  },
  {
    id: 2,
    nickname: '沈砚之',
    avatar: '',
    content: '从你的 Vue 3 组合式 API 那篇文章过来的，写得非常清晰。顺便问一句，站点用的什么字体？显示效果很惊艳。',
    createdAt: new Date(Date.now() - 86400000 * 1).toISOString(),
    likesCount: 8
  },
  {
    id: 3,
    nickname: 'Alex Chen',
    website: 'https://alexchen.io',
    avatar: '',
    content: "Found this blog via a friend's recommendation. The content quality is outstanding — especially the architecture posts. Looking forward to more deep dives!",
    createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    likesCount: 21
  },
  {
    id: 4,
    nickname: '墨白',
    avatar: '',
    content: '收藏夹 +1，以后常来。',
    createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
    likesCount: 5
  },
  {
    id: 5,
    nickname: '苏半夏',
    website: 'https://banxia.me',
    avatar: '',
    content: '友链已加，求互链～ 我的站点是 banxia.me，做独立开发随笔的。',
    createdAt: new Date(Date.now() - 86400000 * 7).toISOString(),
    likesCount: 6,
    replies: [
      {
        id: 102,
        nickname: 'Rosetta',
        avatar: '',
        content: '已收到，稍后会在友链页添加上 👍',
        createdAt: new Date(Date.now() - 86400000 * 6.8).toISOString(),
        likesCount: 2
      }
    ]
  }
])

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return ''
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffMins < 1) return t('common.justNow') || '刚刚'
  if (diffMins < 60) return `${diffMins} ${t('common.minutesAgo') || '分钟前'}`
  if (diffHours < 24) return `${diffHours} ${t('common.hoursAgo') || '小时前'}`
  if (diffDays < 30) return `${diffDays} ${t('common.daysAgo') || '天前'}`
  return date.toLocaleDateString()
}

const submitGuestbook = () => {
  if (!form.nickname.trim() || !form.content.trim()) return
  const newItem: GuestbookItem = {
    id: Date.now(),
    nickname: form.nickname,
    email: form.email,
    website: form.website,
    content: form.content,
    createdAt: new Date().toISOString(),
    likesCount: 0,
    replies: []
  }
  guestbookList.value.unshift(newItem)
  form.nickname = ''
  form.email = ''
  form.website = ''
  form.content = ''
}

const toggleLike = (item: GuestbookItem) => {
  item.liked = !item.liked
  item.likesCount += item.liked ? 1 : -1
}

const toggleReplyLike = (reply: ReplyItem) => {
  reply.liked = !reply.liked
  reply.likesCount += reply.liked ? 1 : -1
}

const toggleReplyInput = (item: GuestbookItem) => {
  replyOpenId.value = replyOpenId.value === item.id ? null : item.id
  if (replyOpenId.value) {
    replyForm.nickname = ''
    replyForm.email = ''
    replyForm.website = ''
    replyForm.content = ''
  }
}

const submitReply = (item: GuestbookItem) => {
  if (!replyForm.nickname.trim() || !replyForm.content.trim()) return
  const newReply: ReplyItem = {
    id: Date.now(),
    nickname: replyForm.nickname,
    email: replyForm.email,
    website: replyForm.website,
    content: replyForm.content,
    createdAt: new Date().toISOString(),
    likesCount: 0
  }
  if (!item.replies) item.replies = []
  item.replies.push(newReply)
  replyOpenId.value = null
  replyForm.nickname = ''
  replyForm.email = ''
  replyForm.website = ''
  replyForm.content = ''
}
</script>
