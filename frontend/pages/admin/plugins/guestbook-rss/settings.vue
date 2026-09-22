<script setup lang="ts">
/**
 * Guestbook RSS 插件 · 原生后台设置页。
 *
 * 路由 /admin/plugins/guestbook-rss/settings（静态路由，优先于
 * [slug]/[...catchall].vue 通用 iframe 承载页）。
 *
 * 数据：
 * - GET  /admin/plugins/guestbook-rss/settings → 当前设置
 * - PUT  /admin/plugins/guestbook-rss/settings → 持久化设置
 * 另有公开 feed：/api/plugins/guestbook-rss/feed.xml
 */
import { ArrowLeft, ExternalLink, Rss, Save, Loader2 } from '@lucide/vue'
import { toast } from 'vue-sonner'
import { apiFetch } from '~~/composables/useApi'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Switch } from '~~/components/ui/switch'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'

definePageMeta({ ssr: false, layout: 'admin' })

interface GuestbookSettings {
  feed_title: string
  feed_description: string
  max_items: number
  include_author_email: boolean
  language: string
}

const defaults: GuestbookSettings = {
  feed_title: 'Rosetta 留言板 RSS',
  feed_description: '最近 50 条公开留言',
  max_items: 50,
  include_author_email: false,
  language: 'zh-CN'
}

const form = reactive<GuestbookSettings>({ ...defaults })
const loading = ref(true)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const resp = await apiFetch<{ success: boolean, data: GuestbookSettings }>(
      '/admin/plugins/guestbook-rss/settings',
      { method: 'GET' }
    )
    if (resp?.data) Object.assign(form, defaults, resp.data)
  } catch {
    /* apiFetch 已提示 */
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await apiFetch('/admin/plugins/guestbook-rss/settings', {
      method: 'PUT',
      body: { ...form }
    })
    toast.success('设置已保存')
  } catch {
    /* apiFetch 已提示 */
  } finally {
    saving.value = false
  }
}

const goBack = () => navigateTo('/admin/system/plugins')
const openFeed = () => window.open('/api/plugins/guestbook-rss/feed.xml', '_blank', 'noopener,noreferrer')

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-4 max-w-3xl">
    <!-- 顶部条 -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3 min-w-0">
        <Button
          size="sm"
          variant="ghost"
          class="shrink-0"
          @click="goBack"
        >
          <ArrowLeft data-icon="inline-start" />
          返回插件管理
        </Button>
        <div class="min-w-0">
          <h1 class="text-xl md:text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Rss class="size-5 text-primary" />
            留言板 RSS
            <Badge
              variant="outline"
              class="font-mono text-[11px]"
            >
              v0.1.0
            </Badge>
          </h1>
          <p class="text-sm text-muted-foreground mt-0.5">
            配置留言板公开 RSS feed 的输出内容
          </p>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        @click="openFeed"
      >
        <ExternalLink data-icon="inline-start" />
        查看 Feed
      </Button>
    </div>

    <Card>
      <CardHeader>
        <CardTitle>Feed 设置</CardTitle>
        <CardDescription>
          修改将保存到站点设置并立即对 feed 阅读器生效
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="loading"
          class="flex items-center gap-2 py-10 text-muted-foreground"
        >
          <Loader2 class="size-4 animate-spin" />
          正在加载设置…
        </div>
        <form
          v-else
          class="flex flex-col gap-5"
          @submit.prevent="save"
        >
          <!-- 标题 -->
          <div class="flex flex-col gap-2">
            <Label for="feed-title">
              RSS 频道标题
            </Label>
            <Input
              id="feed-title"
              v-model="form.feed_title"
              placeholder="Rosetta 留言板 RSS"
            />
          </div>

          <!-- 描述 -->
          <div class="flex flex-col gap-2">
            <Label for="feed-desc">
              RSS 频道描述
            </Label>
            <Textarea
              id="feed-desc"
              v-model="form.feed_description"
              rows="3"
              placeholder="最近 50 条公开留言"
            />
          </div>

          <div class="grid sm:grid-cols-2 gap-5">
            <!-- 最大条数 -->
            <div class="flex flex-col gap-2">
              <Label for="max-items">
                最多输出条数
              </Label>
              <Input
                id="max-items"
                v-model.number="form.max_items"
                type="number"
                min="1"
                max="200"
              />
              <p class="text-xs text-muted-foreground">
                范围 1–200
              </p>
            </div>

            <!-- 语言 -->
            <div class="flex flex-col gap-2">
              <Label for="feed-language">
                RSS 语言标签
              </Label>
              <Select v-model="form.language">
                <SelectTrigger id="feed-language">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="zh-CN">
                    zh-CN
                  </SelectItem>
                  <SelectItem value="zh-TW">
                    zh-TW
                  </SelectItem>
                  <SelectItem value="en-US">
                    en-US
                  </SelectItem>
                  <SelectItem value="ja-JP">
                    ja-JP
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <!-- 包含邮箱 -->
          <div class="flex items-center justify-between gap-3 rounded-lg border p-3.5">
            <div class="flex flex-col gap-0.5">
              <Label>包含作者邮箱</Label>
              <span class="text-xs text-muted-foreground">
                在条目内输出 &lt;author&gt;；关闭时仅输出 Dublin Core 作者名
              </span>
            </div>
            <Switch v-model="form.include_author_email" />
          </div>

          <div class="flex justify-end">
            <Button
              type="submit"
              :disabled="saving"
            >
              <Save
                v-if="!saving"
                data-icon="inline-start"
              />
              <Loader2
                v-else
                class="animate-spin"
                data-icon="inline-start"
              />
              {{ saving ? '保存中…' : '保存设置' }}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
