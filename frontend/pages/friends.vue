<!--
  友情链接页：useFriendLinks → GET /friend-links 的卡片网格。
  后台打开 features.enable_friend_apply 时页尾追加「申请友链」表单 →
  POST /friend-links/apply，提交的内容一律以 pending 入审核队列（管理员在
  /admin/friend-links 裁决），所以表单提交成功后不刷新列表：公示列表没变。
  硬契约：数据必须同步解构、禁止加 await —— async setup 在客户端 hydrate 阶段被当成
  pending Promise，Suspense 渲染 v-cmt 注释节点，与 SSR 已输出的真实 DOM 直接 mismatch。
  logoFailedIds 首渲染必须为空集（两端一致），失败时整组替换新 Set，原地 add 不触发渲染。
-->
<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-primary/10 via-accent/10 to-primary/5 mb-5">
        <Link2 class="size-7 text-success" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('friends.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('friends.desc') }}
      </p>
    </header>

    <div
      v-if="loading"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
    >
      <Skeleton
        v-for="i in 4"
        :key="i"
        class="h-48 rounded-2xl"
      />
    </div>

    <div
      v-else-if="fetchError"
      class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
    >
      {{ t('friends.loadFailed', '加载失败') }}
    </div>

    <div
      v-else-if="friendLinks.length"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
    >
      <a
        v-for="friend in friendLinks"
        :key="friend.id"
        :href="friend.url"
        :target="friend.target_blank ? '_blank' : undefined"
        :rel="friend.target_blank ? 'noopener noreferrer' : undefined"
      >
        <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden">
          <CardHeader class="p-5 pb-3">
            <div class="flex items-start gap-3 mb-3">
              <div
                class="size-12 shrink-0 rounded-xl flex items-center justify-center overflow-hidden bg-muted transition-transform duration-300 group-hover:scale-105"
              >
                <img
                  v-if="friend.logo && !logoFailedIds.has(friend.id)"
                  :src="friend.logo"
                  :alt="pickLocalized(friend.name)"
                  class="size-full object-cover"
                  loading="lazy"
                  width="48"
                  height="48"
                  @error="onLogoError(friend.id)"
                >
                <span
                  v-else
                  class="font-display text-lg font-bold text-muted-foreground"
                >
                  {{ pickLocalized(friend.name)?.[0]?.toUpperCase() }}
                </span>
              </div>
              <div class="flex-1 min-w-0">
                <CardTitle class="font-display text-base tracking-tight group-hover:underline underline-offset-4 truncate">
                  {{ pickLocalized(friend.name) }}
                </CardTitle>
              </div>
            </div>
            <CardDescription class="line-clamp-3 text-sm leading-relaxed min-h-[3.75rem]">
              {{ pickLocalized(friend.description) || t('friends.noDesc') }}
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

    <div
      v-else
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Link2 class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('friends.noLinks') }}
      </h3>
      <p class="text-muted-foreground mt-2 text-sm max-w-md mx-auto leading-relaxed">
        {{ t('friends.emptyHint') }}
      </p>
      <NuxtLink
        :to="localeHref('/guestbook')"
        :class="cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'mt-6')"
      >
        <MessageSquare class="size-4" />
        {{ t('common.guestbook') }}
      </NuxtLink>
    </div>

    <!--
      友链申请表单。出现条件与后端闸门读同一项（features.enable_friend_apply）：
      关闭时接口回 403 FRIEND_APPLY_DISABLED，这里连表单都不该渲染，
      留一个点了就报错的按钮比没有按钮更糟。
    -->
    <Card
      v-if="applyEnabled"
      class="mt-12 max-w-2xl mx-auto"
    >
      <CardHeader class="pb-4">
        <CardTitle class="text-lg flex items-center gap-2">
          <Link2 class="size-4 text-muted-foreground" />
          {{ t('friends.applyTitle') }}
        </CardTitle>
        <CardDescription class="text-sm leading-relaxed">
          {{ t('friends.applyDesc') }}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          class="grid gap-4"
          @submit.prevent="submitApplication"
        >
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              v-model="form.name"
              :placeholder="t('friends.applyName')"
              :aria-label="t('friends.applyName')"
              maxlength="100"
              :disabled="submitting"
            />
            <Input
              v-model="form.url"
              type="url"
              inputmode="url"
              :placeholder="t('friends.applyUrl')"
              :aria-label="t('friends.applyUrl')"
              maxlength="500"
              :disabled="submitting"
            />
          </div>
          <Input
            v-model="form.description"
            :placeholder="t('friends.applyDescription')"
            :aria-label="t('friends.applyDescription')"
            maxlength="200"
            :disabled="submitting"
          />
          <Input
            v-model="form.logo"
            type="url"
            inputmode="url"
            :placeholder="t('friends.applyLogo')"
            :aria-label="t('friends.applyLogo')"
            maxlength="500"
            :disabled="submitting"
          />
          <CaptchaField
            v-if="needCaptcha"
            ref="captchaRef"
            :enabled="needCaptcha"
          />
          <!-- 校验失败必须写行内 submitError：静默 return 的表现是"点了提交，什么都没发生" -->
          <p
            v-if="submitError"
            class="text-sm text-error"
            role="alert"
          >
            {{ submitError }}
          </p>
          <div class="flex justify-end">
            <Button
              type="submit"
              :disabled="submitting"
            >
              <Send
                v-if="!submitting"
                data-icon="inline-start"
                class="mr-2"
              />
              <Loader2
                v-else
                data-icon="inline-start"
                class="animate-spin mr-2"
              />
              {{ submitting ? t('common.submitting') : t('friends.applySubmit') }}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '~~/components/ui/card'
import { Skeleton } from '~~/components/ui/skeleton'
import { Button, buttonVariants } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import CaptchaField from '~~/components/CaptchaField.vue'
import { useFriendLinks } from '~~/composables/useFriendLinks'
import { apiFetch } from '~~/composables/useApi'
import { useToast } from '~~/composables/useToast'
import { useAuthStore } from '~~/stores/auth'
import { cn, extractApiErrorMessage } from '~~/lib/utils'
import type { FriendLinkApplyReceipt } from '~~/types/api'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Link2, ExternalLink, MessageSquare, Send } from '@lucide/vue'
import { Loader2 } from '~~/lib/lucide-svg-icons'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const { localeHref } = useLocaleLink()
const site = useSite()
const toast = useToast()
const authStore = useAuthStore()

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

// ===== SEO：基于 i18n + 站点设置 =====
useSeo({
  title: computed(() => String(t('nav.friends') || t('friends.title') || '友情链接')),
  description: computed(() => site.siteDescription.value),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.friends') as string, url: '/friends' }
])

const { getFriendLinks } = useFriendLinks()

// ===== Hydration 安全：同步解构（无 await）避免 setup() 被编译器判定为 async 函数。
// async setup 在客户端同步 Hydrate Diff 阶段视为 Promise pending → Suspense 渲染 Symbol(v-cmt) Comment，
// 而 SSR 端已经渲染了真实 div 子树 → 直接触发 "Hydration completed but contains mismatches."。
// useFriendLinks/getFriendLinks 内部基于 useFetch，返回 { data, pending, error } 同步解构即可，
// 首字节 SSR 数据由 useFetch 在服务端阶段填充，客户端从 payload 取回，不需要 await 阻塞。
const { data: links, pending: loading, error: fetchError } = getFriendLinks()

const friendLinks = computed(() => links.value ?? [])

// Logo 加载失败 → 回退到首字母占位（整集替换保证响应式触发；空集两端一致，无 Hydration 风险）
const logoFailedIds = ref<Set<string | number>>(new Set())
const onLogoError = (id: string | number) => {
  const next = new Set(logoFailedIds.value)
  next.add(id)
  logoFailedIds.value = next
}

// ===== 友链申请（features.enable_friend_apply）=====
// 与后端 api/core.py::apply_friend_link 的闸门读同一项：关闭时接口回 403，
// 表单必须一起收起，否则用户面对的是一个点了就报错的按钮。
const applyEnabled = computed(() => site.features.value.enable_friend_apply)
// 验证码只挡未登录访客（后端 ensure_captcha_for_guest 同一判据），登录用户免验。
const needCaptcha = computed(() => !authStore.isAuthenticated && site.features.value.enable_captcha)
const captchaRef = ref<InstanceType<typeof CaptchaField> | null>(null)

const form = reactive({ name: '', url: '', description: '', logo: '' })
const submitting = ref(false)
const submitError = ref<string | null>(null)

// 写入口的必填/绝对地址判据在前端先跑一遍：后端 422 是兜底，不是首道门，
// 而且 422 的正文是 Pydantic 结构，行内提示比它好读。
const URL_SCHEME_RE = /^https?:\/\//i

const submitApplication = async () => {
  if (submitting.value) return
  const name = form.name.trim()
  const url = form.url.trim()
  if (name.length < 2) {
    submitError.value = String(t('friends.applyNameRequired'))
    return
  }
  if (!URL_SCHEME_RE.test(url)) {
    submitError.value = String(t('friends.applyUrlInvalid'))
    return
  }
  if (needCaptcha.value && !captchaRef.value?.valid()) {
    submitError.value = String(t('captcha.required'))
    return
  }

  submitting.value = true
  submitError.value = null
  try {
    const payload: Record<string, string> = { name, url, ...(captchaRef.value?.payload() ?? {}) }
    if (form.description.trim()) payload.description = form.description.trim()
    if (form.logo.trim()) payload.logo = form.logo.trim()

    const receipt = await apiFetch<FriendLinkApplyReceipt>('/friend-links/apply', {
      method: 'POST',
      body: payload
    })

    // 文案按回执分支，而不是照抄服务端的中文 message（那是单语的，四语页面会串语言）：
    // duplicate + approved＝这个站早就公示了；duplicate + pending＝别刷同一行；
    // 新建的行走 pending，所以**不刷新列表**——pending 不在公开读口的 SQL 谓词里，
    // 刷新只会拿到同一份公示列表，白打一次接口。
    const key
      = receipt.duplicate && receipt.status === 'approved'
        ? 'friends.applyAlreadyListed'
        : receipt.duplicate
          ? 'friends.applyDuplicate'
          : 'friends.applySuccess'
    toast.success(String(t(key)))
    form.name = ''
    form.url = ''
    form.description = ''
    form.logo = ''
  } catch (err: unknown) {
    const e = (err ?? {}) as Record<string, unknown>
    submitError.value = extractApiErrorMessage(e.data, String(t('friends.applyFailed')))
    // apiFetch 抛错前已统一 toast（silentToast 默认 false），这里只写行内错误，不双报。
  } finally {
    // 验证码答案一次性：服务端无论校验成败都已 consume，不换一张重试就永远撞 CAPTCHA_EXPIRED。
    if (needCaptcha.value) captchaRef.value?.refresh()
    submitting.value = false
  }
}
</script>
