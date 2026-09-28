<!--
  账户设置 /account/settings（SPA + no-store，继承 routeRules 的 /account/** 反选）：
  接上后端自上线起"就绪、前端零消费"的三组写端点 ——
    PUT  /users/me            资料（昵称/简介/网站/GitHub/QQ/头像来源/封面图）
    GET/PUT /users/me/preferences  隐私偏好（5 个真实生效的开关）
    POST /users/me/password   改密（成功即全端下线）
  三条硬约束：
  1. 偏好里的 ``theme`` 字段**故意不做 UI**：models/user.py 里它没有任何消费点
     （前台主题由 useFrontendTheme + 主题系统决定），放个开关等于骗用户"设置了但没用"。
     五个隐私开关都有真实强制点：public_profile→资料主文档与其子资源（posts/comments/stats/preferences）统一
     404、show_email→响应 helper、show_posts/show_comments→作者归档与评论列表「隐藏即空」、
     show_stats→资料读数全零。
  2. 改密成功必须清登录态并跳 /login：后端会 bump token_version 使全部会话失效，
     前端若留在原页，下一个请求就是 401 自动刷新失败 → 被 useAPI 打回登录页，
     用户看到的是"我刚保存就掉线"，而不是"请用小密码重新登录"。
  3. 校验只走一条通道（AGENTS §10.5）：长度/一致性等前端可判的走 FormMessage 位内联提示，
     强度规则（WEAK_PASSWORD 422）与旧密码错误交给 apiFetch 的统一 toast，不双报。
  另：本表单的「旧密码错误」在后端刻意是 400 而不是 401 —— 带有效 token 的请求回 401
  会触发 apiFetch 的刷新重试链，重试仍 401 就清 token 跳登录，打错一个字就被整站登出。
-->
<template>
  <div class="container py-16 max-w-3xl mx-auto">
    <header class="mb-10">
      <NuxtLink
        to="/account"
        class="inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft data-icon="inline-start" />
        {{ t('account.backToAccount') }}
      </NuxtLink>
      <h1 class="mt-4 font-display text-2xl md:text-3xl font-bold tracking-tight">
        {{ t('account.settingsTitle') }}
      </h1>
      <p class="mt-1 text-sm text-muted-foreground">
        {{ t('account.settingsDesc') }}
      </p>
    </header>

    <!-- ===== 个人资料 ===== -->
    <section
      class="card-surface mb-8 rounded-xl p-6"
      aria-labelledby="settings-profile-heading"
    >
      <h2
        id="settings-profile-heading"
        class="font-display text-lg font-semibold"
      >
        {{ t('account.sectionProfile') }}
      </h2>
      <p class="mt-1 text-sm text-muted-foreground">
        {{ t('account.sectionProfileHint') }}
      </p>

      <form
        class="mt-6 flex flex-col gap-5"
        @submit.prevent="saveProfile"
      >
        <div class="flex flex-col gap-2">
          <Label for="profile-cover">{{ t('account.fieldCover') }}</Label>
          <div
            v-if="profile.cover_image"
            class="overflow-hidden rounded-xl border"
          >
            <img
              :src="profile.cover_image"
              :alt="t('account.fieldCover')"
              class="h-32 w-full object-cover"
            >
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <input
              id="profile-cover"
              ref="coverInput"
              type="file"
              accept="image/*"
              class="hidden"
              :disabled="savingProfile || coverUploading"
              @change="handleCoverUpload"
            >
            <Button
              type="button"
              variant="outline"
              size="sm"
              :disabled="savingProfile || coverUploading"
              @click="coverInput?.click()"
            >
              <LoaderCircle
                v-if="coverUploading"
                data-icon="inline-start"
                class="animate-spin"
              />
              <ImagePlus
                v-else
                data-icon="inline-start"
              />
              {{ profile.cover_image ? t('account.coverReplace') : t('account.coverUpload') }}
            </Button>
            <Button
              v-if="profile.cover_image"
              type="button"
              variant="ghost"
              size="sm"
              :disabled="savingProfile || coverUploading"
              @click="profile.cover_image = ''"
            >
              {{ t('account.coverRemove') }}
            </Button>
          </div>
          <p class="text-xs text-muted-foreground">
            {{ t('account.fieldCoverHint') }}
          </p>
        </div>

        <div class="flex flex-col gap-2">
          <Label for="profile-nickname">{{ t('account.fieldNickname') }}</Label>
          <Input
            id="profile-nickname"
            v-model="profile.nickname"
            :maxlength="LIMITS.nickname"
            :disabled="savingProfile"
          />
          <p
            v-if="profileErrors.nickname"
            class="text-sm text-destructive"
          >
            {{ profileErrors.nickname }}
          </p>
        </div>

        <div class="flex flex-col gap-2">
          <Label for="profile-bio">{{ t('account.fieldBio') }}</Label>
          <Textarea
            id="profile-bio"
            v-model="profile.bio"
            :maxlength="LIMITS.bio"
            rows="4"
            :disabled="savingProfile"
          />
          <p
            v-if="profileErrors.bio"
            class="text-sm text-destructive"
          >
            {{ profileErrors.bio }}
          </p>
        </div>

        <div class="grid gap-5 sm:grid-cols-2">
          <div class="flex flex-col gap-2">
            <Label for="profile-website">{{ t('account.fieldWebsite') }}</Label>
            <!-- 不做 type="url" 的原生校验：后端 UserBase 对 website/github 会补 https:// 前缀，
                 前端若按 URL 规范拒绝裸域名，就把一个后端愿意接受的输入拦在了表单里（两端严格度不一致）。 -->
            <Input
              id="profile-website"
              v-model="profile.website"
              :maxlength="LIMITS.website"
              :disabled="savingProfile"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="profile-github">{{ t('account.fieldGithub') }}</Label>
            <Input
              id="profile-github"
              v-model="profile.github"
              :maxlength="LIMITS.github"
              :disabled="savingProfile"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="profile-qq">{{ t('account.fieldQq') }}</Label>
            <Input
              id="profile-qq"
              v-model="profile.qq"
              :maxlength="LIMITS.qq"
              :disabled="savingProfile"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="profile-avatar-source">{{ t('account.fieldAvatarSource') }}</Label>
            <Select
              v-model="profile.avatar_source"
              :disabled="savingProfile"
            >
              <SelectTrigger
                id="profile-avatar-source"
                class="w-full"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="opt in avatarSourceOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">
              {{ t('account.fieldAvatarSourceHint') }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <Button
            type="submit"
            :disabled="savingProfile"
          >
            <LoaderCircle
              v-if="savingProfile"
              data-icon="inline-start"
              class="animate-spin"
            />
            {{ t('account.saveProfile') }}
          </Button>
        </div>
      </form>
    </section>

    <!-- ===== 隐私偏好 ===== -->
    <section
      class="card-surface mb-8 rounded-xl p-6"
      aria-labelledby="settings-privacy-heading"
    >
      <h2
        id="settings-privacy-heading"
        class="font-display text-lg font-semibold"
      >
        {{ t('account.sectionPrivacy') }}
      </h2>
      <p class="mt-1 text-sm text-muted-foreground">
        {{ t('account.sectionPrivacyHint') }}
      </p>

      <div
        v-if="preferencesPending"
        class="mt-6 flex flex-col gap-4"
      >
        <Skeleton
          v-for="s in 5"
          :key="s"
          class="h-12 w-full rounded-xl"
        />
      </div>

      <div
        v-else-if="preferencesError"
        class="mt-6 text-sm text-destructive"
        role="alert"
      >
        {{ t('account.loadFailed') }}
        <Button
          variant="link"
          size="sm"
          @click="reloadPreferences"
        >
          {{ t('account.retry') }}
        </Button>
      </div>

      <form
        v-else
        class="mt-6 flex flex-col gap-1"
        @submit.prevent="savePreferences"
      >
        <div
          v-for="item in preferenceItems"
          :key="item.key"
          class="flex items-start justify-between gap-4 border-b py-4 last:border-b-0"
        >
          <div class="min-w-0">
            <Label
              :for="`pref-${item.key}`"
              class="cursor-pointer text-sm font-medium"
            >
              {{ item.label }}
            </Label>
            <p class="mt-1 text-xs text-muted-foreground">
              {{ item.hint }}
            </p>
          </div>
          <Switch
            :id="`pref-${item.key}`"
            :model-value="preferences[item.key]"
            :disabled="savingPreferences"
            @update:model-value="(v: boolean) => { preferences[item.key] = v }"
          />
        </div>

        <div class="mt-6 flex items-center gap-3">
          <Button
            type="submit"
            :disabled="savingPreferences"
          >
            <LoaderCircle
              v-if="savingPreferences"
              data-icon="inline-start"
              class="animate-spin"
            />
            {{ t('account.savePreferences') }}
          </Button>
        </div>
      </form>
    </section>

    <!-- ===== 修改密码 ===== -->
    <section
      class="card-surface rounded-xl p-6"
      aria-labelledby="settings-password-heading"
    >
      <h2
        id="settings-password-heading"
        class="font-display text-lg font-semibold"
      >
        {{ t('account.sectionPassword') }}
      </h2>
      <p class="mt-1 text-sm text-muted-foreground">
        {{ t('account.sectionPasswordHint') }}
      </p>

      <form
        class="mt-6 flex flex-col gap-5"
        @submit.prevent="savePassword"
      >
        <div class="flex flex-col gap-2">
          <Label for="pwd-old">{{ t('account.fieldOldPassword') }}</Label>
          <Input
            id="pwd-old"
            v-model="passwords.old"
            type="password"
            autocomplete="current-password"
            :disabled="savingPassword"
          />
        </div>
        <div class="grid gap-5 sm:grid-cols-2">
          <div class="flex flex-col gap-2">
            <Label for="pwd-new">{{ t('account.fieldNewPassword') }}</Label>
            <Input
              id="pwd-new"
              v-model="passwords.new"
              type="password"
              autocomplete="new-password"
              :disabled="savingPassword"
            />
            <p
              v-if="passwordErrors.new"
              class="text-sm text-destructive"
            >
              {{ passwordErrors.new }}
            </p>
          </div>
          <div class="flex flex-col gap-2">
            <Label for="pwd-confirm">{{ t('account.fieldConfirmPassword') }}</Label>
            <Input
              id="pwd-confirm"
              v-model="passwords.confirm"
              type="password"
              autocomplete="new-password"
              :disabled="savingPassword"
            />
            <p
              v-if="passwordErrors.confirm"
              class="text-sm text-destructive"
            >
              {{ passwordErrors.confirm }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <Button
            type="submit"
            variant="destructive"
            :disabled="savingPassword"
          >
            <LoaderCircle
              v-if="savingPassword"
              data-icon="inline-start"
              class="animate-spin"
            />
            {{ t('account.savePassword') }}
          </Button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, ImagePlus, LoaderCircle } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import { Skeleton } from '~~/components/ui/skeleton'
import { Switch } from '~~/components/ui/switch'
import { Textarea } from '~~/components/ui/textarea'
import { apiFetch, useAPI } from '~~/composables/useApi'
import { useMediaUploadCover } from '~~/composables/useMedia'
import { useToast } from '~~/composables/useToast'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'

/* UserPreferenceResponse 里前端要用的字段（theme 是死字段，见文件头约束 1） */
interface UserPreferences {
  public_profile: boolean
  show_email: boolean
  show_posts: boolean
  show_comments: boolean
  show_stats: boolean
}
interface ProfileForm {
  nickname: string
  bio: string
  website: string
  github: string
  qq: string
  avatar_source: string
  cover_image: string
}

// 上限与后端 UserUpdate 的 Field(max_length=...) 同口径，超了先在前端拦住，省一次 422 往返
const LIMITS = { nickname: 50, bio: 500, website: 200, github: 200, qq: 20 } as const
const AVATAR_SOURCES = ['auto', 'custom', 'github', 'qq', 'gravatar'] as const

// ssr:false 由 routeRules 的 /account/** 覆盖，页面不重复声明第二套口径。
definePageMeta({ layout: 'default', middleware: 'auth-required' })

const { t, locale } = useI18n()
const toast = useToast()
const authStore = useAuthStore()

const authUser = computed(() => authStore.user as Record<string, unknown> | null)

const profile = reactive<ProfileForm>({
  nickname: '',
  bio: '',
  website: '',
  github: '',
  qq: '',
  avatar_source: 'auto',
  cover_image: ''
})
const profileErrors = reactive<Record<string, string>>({})
const savingProfile = ref(false)
const coverInput = ref<HTMLInputElement | null>(null)
const coverUploading = ref(false)

/** 首帧用 store 里已有的 /users/me 结果回填，避免表单先空一次再跳值 */
function seedProfile() {
  const u = authUser.value
  if (!u) return
  profile.nickname = String(u.nickname ?? '')
  profile.bio = String(u.bio ?? '')
  profile.website = String(u.website ?? '')
  profile.github = String(u.github ?? '')
  profile.qq = String(u.qq ?? '')
  profile.avatar_source = String(u.avatar_source ?? 'auto')
  profile.cover_image = String(u.cover_image ?? '')
}
seedProfile()
watch(authUser, seedProfile)

const avatarSourceOptions = computed(() =>
  AVATAR_SOURCES.map(value => ({
    value,
    // 键名与后端枚举值一一对应（auto/custom/github/qq/gravatar），保持 account.avatarSource* 平铺
    label: t(`account.avatarSource${value.charAt(0).toUpperCase()}${value.slice(1)}`)
  }))
)

function validateProfile(): boolean {
  profileErrors.nickname = profile.nickname.length > LIMITS.nickname
    ? t('account.tooLong', { max: LIMITS.nickname })
    : ''
  profileErrors.bio = profile.bio.length > LIMITS.bio
    ? t('account.tooLong', { max: LIMITS.bio })
    : ''
  return !profileErrors.nickname && !profileErrors.bio
}

async function saveProfile() {
  if (!validateProfile()) return
  savingProfile.value = true
  try {
    await apiFetch('/users/me', {
      method: 'PUT',
      body: {
        nickname: profile.nickname,
        bio: profile.bio,
        website: profile.website,
        github: profile.github,
        qq: profile.qq,
        avatar_source: profile.avatar_source,
        // 清空必须写 null 而不是 ''：后端 model_dump(exclude_unset=True) 会把显式 null
        // 落成 SQL NULL，而 '' 会留下一个空字符串封面——读取侧按真值判断，
        // '' 是假值、null 也是假值，但只有 null 才是"没有封面"的真实存储形态。
        cover_image: profile.cover_image || null
      }
    })
    // 顶栏头像/昵称与作者卡片读的都是 store，不回读就还是改之前的样子
    await authStore.fetchUser()
    toast.success(t('account.profileSaved'))
  } catch {
    // 失败提示由 apiFetch 按统一信封负责
  } finally {
    savingProfile.value = false
  }
}

/** 封面走 POST /media/cover 拿 URL，再随「保存资料」一起写入：本卡片只有一个写入口。 */
async function handleCoverUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  coverUploading.value = true
  try {
    const res = await useMediaUploadCover(file)
    if (res?.url) profile.cover_image = res.url
  } catch {
    // 上传失败提示由 apiFetch 统一 toast
  } finally {
    coverUploading.value = false
    input.value = ''
  }
}

// ===== 隐私偏好：GET 走 useAPI（自动带 Authorization），PUT 走 apiFetch =====
const {
  data: preferenceData,
  pending: preferencesPending,
  error: preferencesError,
  refresh: reloadPreferences
} = useAPI<Partial<UserPreferences> & { theme?: string | null }>(
  '/users/me/preferences',
  { key: computed(() => `account:preferences:${locale.value}`) }
)

const preferences = reactive<UserPreferences>({
  public_profile: true,
  show_email: false,
  show_posts: true,
  show_comments: true,
  show_stats: true
})
const savingPreferences = ref(false)

/** 默认值必须与后端模型默认一致：偏好行可能压根不存在（注册后没动过设置） */
watch(preferenceData, (data) => {
  if (!data) return
  preferences.public_profile = data.public_profile ?? true
  preferences.show_email = data.show_email ?? false
  preferences.show_posts = data.show_posts ?? true
  preferences.show_comments = data.show_comments ?? true
  preferences.show_stats = data.show_stats ?? true
})

const preferenceItems = computed(() => [
  { key: 'public_profile' as const, label: t('account.prefPublicProfile'), hint: t('account.prefPublicProfileHint') },
  { key: 'show_email' as const, label: t('account.prefShowEmail'), hint: t('account.prefShowEmailHint') },
  { key: 'show_posts' as const, label: t('account.prefShowPosts'), hint: t('account.prefShowPostsHint') },
  { key: 'show_comments' as const, label: t('account.prefShowComments'), hint: t('account.prefShowCommentsHint') },
  { key: 'show_stats' as const, label: t('account.prefShowStats'), hint: t('account.prefShowStatsHint') }
])

async function savePreferences() {
  savingPreferences.value = true
  try {
    await apiFetch('/users/me/preferences', {
      method: 'PUT',
      body: { ...preferences }
    })
    toast.success(t('account.preferencesSaved'))
  } catch {
    // 同上
  } finally {
    savingPreferences.value = false
  }
}

// ===== 修改密码 =====
const passwords = reactive({ old: '', new: '', confirm: '' })
const passwordErrors = reactive<Record<string, string>>({})
const savingPassword = ref(false)

async function savePassword() {
  passwordErrors.new = passwords.new !== passwords.confirm ? t('account.passwordMismatch') : ''
  passwordErrors.confirm = passwordErrors.new
  if (passwordErrors.new) return

  savingPassword.value = true
  try {
    const res = await apiFetch<{ message?: string }>('/users/me/password', {
      method: 'POST',
      body: { old_password: passwords.old, new_password: passwords.new }
    })
    // 后端已使全部会话失效：这里主动清态并说明原因，别等下一个请求 401 掉线
    authStore.clearTokens()
    toast.success(res?.message || t('account.passwordChanged'))
    await navigateTo('/login')
  } catch {
    // 旧密码错误 / 强度不足：apiFetch 已 toast，用户留在本页改输入即可
  } finally {
    savingPassword.value = false
  }
}

useHead(() => ({ title: `${t('account.settingsTitle')} · ${locale.value}` }))
</script>

<style scoped>
/* 沿用 /account 的排版令牌，本文件不引入新皮肤（主题样式零依赖）。 */
</style>
