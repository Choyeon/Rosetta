<!-- 编辑用户页：超级管理员修改指定用户的资料、RBAC 角色、启用/封禁、密码与头衔。
     契约：AdminUserUpdateFull 为 extra=forbid——title_id/is_superuser 不在白名单（头衔走独立
     assign/remove 端点、超管标记由 role 反推），一次「保存」实为最多三次串行请求；
     初始 avatar 是解析后的直链，必须 diff 后才回写，否则派生 URL 被固化进自定义头像列。 -->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="编辑用户"
      description="修改账号资料、角色与启用状态"
      :icon="UserCog"
    >
      <template #actions>
        <Button
          variant="outline"
          size="sm"
          @click="goBack"
        >
          <ArrowLeft data-icon="inline-start" />
          返回用户列表
        </Button>
      </template>
    </AdminPageHeader>

    <!-- 权限提示：GET/PUT /admin/users/{id} 均为 CurrentSuperUser -->
    <Alert
      v-if="!isSuperuser"
      variant="warning"
    >
      <AlertTitle>仅超级管理员可访问</AlertTitle>
      <AlertDescription>
        编辑用户需要超级管理员权限（后端接口仅对 superuser 开放）。如需调整用户资料，请联系超级管理员。
      </AlertDescription>
    </Alert>

    <!-- 后端拒绝自助修改（400），此处直接挡在 UI 层 -->
    <Alert v-else-if="isSelf">
      <AlertTitle>不能在此页面修改自己的账号</AlertTitle>
      <AlertDescription>
        管理员接口禁止修改当前登录账号自身的信息，请通过「个人设置」页面维护自己的资料。
      </AlertDescription>
    </Alert>

    <div
      v-else-if="loading"
      class="grid grid-cols-1 lg:grid-cols-2 gap-6"
    >
      <AdminCard>
        <div class="flex flex-col gap-6 p-6">
          <div class="flex items-center gap-4">
            <Skeleton class="size-20 rounded-full" />
            <Skeleton class="h-9 w-28 rounded-lg" />
          </div>
          <div class="flex flex-col gap-4">
            <Skeleton class="h-10 w-full rounded-lg" />
            <Skeleton class="h-10 w-full rounded-lg" />
            <Skeleton class="h-10 w-full rounded-lg" />
          </div>
        </div>
      </AdminCard>
      <AdminCard>
        <div class="flex flex-col gap-6 p-6">
          <Skeleton class="h-20 w-full rounded-lg" />
          <Skeleton class="h-20 w-full rounded-lg" />
        </div>
      </AdminCard>
    </div>

    <AdminCard v-else-if="loadError || !user">
      <div class="flex flex-col items-start gap-3 p-6">
        <Alert variant="destructive">
          <AlertTitle>加载用户详情失败</AlertTitle>
          <AlertDescription>
            {{ loadErrorMsg || '请求未成功，请重试或返回用户列表。' }}
          </AlertDescription>
        </Alert>
        <div class="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            :disabled="loading"
            @click="retryLoad"
          >
            <RotateCcw data-icon="inline-start" />
            重试
          </Button>
          <Button
            variant="ghost"
            size="sm"
            @click="goBack"
          >
            返回列表
          </Button>
        </div>
      </div>
    </AdminCard>

    <template v-else>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AdminCard>
          <div class="flex items-center gap-2 mb-4">
            <User class="size-5 text-muted-foreground" />
            <span class="text-lg font-semibold">基本资料</span>
          </div>
          <div class="flex flex-col gap-6">
            <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <UserAvatar
                :avatar="form.avatar || null"
                :seed="user.username"
                :name="form.nickname || user.username"
                :title="user.title || null"
                :size="80"
                :show-title="true"
                class="shrink-0 border-4 border-muted"
              />
              <div class="flex flex-col gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="uploadingAvatar"
                  @click="triggerAvatarUpload"
                >
                  <Loader2
                    v-if="uploadingAvatar"
                    data-icon="inline-start"
                    class="animate-spin"
                  />
                  <Upload
                    v-else
                    data-icon="inline-start"
                  />
                  上传头像
                </Button>
                <p class="text-xs text-muted-foreground">
                  上传后将作为该用户的新头像，保存时生效
                </p>
                <input
                  ref="avatarInputRef"
                  type="file"
                  accept="image/*"
                  class="hidden"
                  @change="onAvatarFileChange"
                >
              </div>
            </div>

            <Separator />

            <div class="flex flex-col gap-4">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="flex flex-col gap-2">
                  <Label for="edit-nickname">昵称</Label>
                  <Input
                    id="edit-nickname"
                    v-model="form.nickname"
                    placeholder="显示名称"
                    maxlength="50"
                  />
                </div>
                <div class="flex flex-col gap-2">
                  <Label for="edit-email">邮箱</Label>
                  <Input
                    id="edit-email"
                    v-model="form.email"
                    type="email"
                    placeholder="user@example.com"
                  />
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="flex flex-col gap-2">
                  <Label for="edit-website">个人网站</Label>
                  <Input
                    id="edit-website"
                    v-model="form.website"
                    placeholder="https://..."
                  />
                </div>
                <div class="flex flex-col gap-2">
                  <Label for="edit-github">GitHub</Label>
                  <Input
                    id="edit-github"
                    v-model="form.github"
                    placeholder="github.com/username"
                  />
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="flex flex-col gap-2">
                  <Label for="edit-qq">QQ 号</Label>
                  <Input
                    id="edit-qq"
                    v-model="form.qq"
                    placeholder="5-11 位数字，用于 QQ 头像"
                    maxlength="20"
                  />
                </div>
                <div class="flex flex-col gap-2">
                  <Label for="edit-avatar-source">头像来源</Label>
                  <Select v-model="form.avatar_source">
                    <SelectTrigger id="edit-avatar-source">
                      <SelectValue placeholder="选择头像来源" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem
                        v-for="s in AVATAR_SOURCES"
                        :key="s.value"
                        :value="s.value"
                      >
                        {{ s.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <p class="text-xs text-muted-foreground">
                头像来源为「自动」时按 自定义头像 → GitHub → QQ → Gravatar 依次解析；强制指定来源后若该项缺失，头像会回退为首字母色块。QQ 需为 5-11 位纯数字。
              </p>
              <div class="flex flex-col gap-2">
                <Label for="edit-bio">自我介绍</Label>
                <Textarea
                  id="edit-bio"
                  v-model="form.bio"
                  rows="4"
                  maxlength="500"
                  placeholder="介绍一下这个用户..."
                  class="resize-none"
                />
              </div>
            </div>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex items-center gap-2 mb-4">
            <Shield class="size-5 text-muted-foreground" />
            <span class="text-lg font-semibold">账号安全</span>
          </div>
          <div class="flex flex-col gap-6">
            <div class="flex flex-col gap-3">
              <div class="text-sm font-medium">
                角色权限
              </div>
              <!-- AdminUserUpdateFull 不支持 is_superuser，且 role 会反向同步 is_staff/is_superuser -->
              <div class="flex flex-col gap-2">
                <Label for="edit-role">RBAC 角色</Label>
                <Select v-model="form.role">
                  <SelectTrigger id="edit-role">
                    <SelectValue placeholder="选择角色" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="r in RBAC_ROLES"
                      :key="r.value"
                      :value="r.value"
                    >
                      {{ r.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p class="text-xs text-muted-foreground">
                  后端当前角色：{{ rbacRoleLabel(user.role) }}；变更角色会自动同步管理员/超级管理员标记。不能分配高于自身层级的角色。
                </p>
              </div>
            </div>

            <Separator />

            <div class="flex flex-col gap-3">
              <div class="text-sm font-medium">
                账号状态
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="flex items-center justify-between rounded-xl border p-3">
                  <div>
                    <div class="text-sm font-medium">
                      已激活
                    </div>
                    <div class="text-xs text-muted-foreground">
                      允许登录
                    </div>
                  </div>
                  <Switch
                    v-model="form.is_active"
                    aria-label="已激活"
                  />
                </div>
                <div class="flex items-center justify-between rounded-xl border p-3">
                  <div>
                    <div class="text-sm font-medium">
                      已封禁
                    </div>
                    <div class="text-xs text-muted-foreground">
                      禁止访问
                    </div>
                  </div>
                  <Switch
                    v-model="form.is_banned"
                    aria-label="已封禁"
                  />
                </div>
              </div>
            </div>

            <Separator />

            <!-- 后端禁止对超级管理员重置密码（403） -->
            <div
              v-if="!user.is_superuser"
              class="flex flex-col gap-3"
            >
              <div class="text-sm font-medium">
                修改密码
              </div>
              <div class="flex flex-col gap-3">
                <div class="flex flex-col gap-2">
                  <Label for="edit-pwd1">新密码</Label>
                  <Input
                    id="edit-pwd1"
                    v-model="pwdForm.newPassword"
                    type="password"
                    placeholder="留空则不修改"
                  />
                  <p class="text-xs text-muted-foreground">
                    至少 8 位，含大小写字母和数字
                  </p>
                </div>
                <div class="flex flex-col gap-2">
                  <Label for="edit-pwd2">确认密码</Label>
                  <Input
                    id="edit-pwd2"
                    v-model="pwdForm.confirmPassword"
                    type="password"
                    placeholder="再次输入新密码"
                  />
                </div>
              </div>
            </div>

            <Separator />

            <div class="flex flex-col gap-2">
              <Label for="edit-title">头衔</Label>
              <!-- title_id 不在 PUT 白名单内，保存时单独调用 titles/assign / delete title 接口 -->
              <Select
                v-model="form.title_id"
                :disabled="titlesLoading"
              >
                <SelectTrigger id="edit-title">
                  <SelectValue placeholder="选择头衔" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem :value="0">
                    无
                  </SelectItem>
                  <SelectItem
                    v-for="t in titles"
                    :key="t.id"
                    :value="t.id ?? 0"
                  >
                    <span class="inline-flex items-center gap-2">
                      <span
                        v-if="t.icon"
                        class="size-4 shrink-0"
                        :style="{ color: t.color || '#3b82f6' }"
                      >
                        <TitleIconSvg
                          :icon="t.icon"
                          :stroke-width="2"
                        />
                      </span>
                      <span>{{ getLocalizedStr(t.name) }}</span>
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </AdminCard>
      </div>

      <div class="flex flex-col items-end gap-2 pt-4">
        <p
          v-if="saveError"
          class="text-sm text-destructive"
        >
          {{ saveError }}
        </p>
        <div class="flex justify-end gap-3">
          <Button
            variant="ghost"
            @click="goBack"
          >
            取消
          </Button>
          <Button
            :disabled="saving"
            @click="saveAll"
          >
            <Loader2
              v-if="saving"
              data-icon="inline-start"
              class="animate-spin"
            />
            保存更改
          </Button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */

import AdminCard from '~~/components/admin/AdminCard.vue'
import UserAvatar from '~~/components/UserAvatar.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Switch } from '~~/components/ui/switch'
import { Separator } from '~~/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Label } from '~~/components/ui/label'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import {
  ArrowLeft, User, Shield, Upload, Loader2, UserCog, RotateCcw
} from '@lucide/vue'
import TitleIconSvg from '~~/components/TitleIconSvg.vue'
import {
  fetchAdminUserDetail,
  updateAdminUserDetail,
  fetchAdminUserTitles,
  resetAdminUserPassword,
  assignAdminUserTitle,
  removeAdminUserTitle,
  RBAC_ROLES,
  rbacRoleLabel,
  type AdminUserRow,
  type AdminUserTitle
} from '~~/composables/useAdminManage'
import { useMediaUploadAvatar } from '~~/composables/useMedia'

definePageMeta({ ssr: false, layout: 'admin' })

const route = useRoute()
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()

const userId = computed(() => {
  const raw = route.params.id
  if (Array.isArray(raw)) return parseInt(raw[0] ?? '', 10)
  return parseInt(raw as string, 10)
})

const isSuperuser = computed(() => auth.user?.is_superuser === true)
// 后端 PUT/POST reset-password 均禁止操作自己（400），提前挡在 UI 层
const isSelf = computed(() => auth.user?.id === userId.value)

const loading = ref(false)
const saving = ref(false)
const titlesLoading = ref(false)
const uploadingAvatar = ref(false)
const loadError = ref(false)
const loadErrorMsg = ref('')
const saveError = ref('')

const user = ref<AdminUserRow | null>(null)
const titles = ref<AdminUserTitle[]>([])
// 头衔变更需单独调接口，记录初始值用于 diff
let originalTitleId = 0
// 头像需 diff 后才回写，见 saveAll 里的说明
let originalAvatar = ''

const form = reactive({
  nickname: '',
  email: '',
  website: '',
  github: '',
  bio: '',
  avatar: '' as string | null,
  qq: '',
  avatar_source: 'auto',
  title_id: 0 as number,
  role: 'subscriber',
  is_active: false,
  is_banned: false
})

const pwdForm = reactive({
  newPassword: '',
  confirmPassword: ''
})

/** 与后端 AvatarSource 字面量一致（backend/services/avatar_resolver.py） */
const AVATAR_SOURCES = [
  { value: 'auto', label: '自动（按优先级回退）' },
  { value: 'custom', label: '自定义上传头像' },
  { value: 'github', label: 'GitHub 头像' },
  { value: 'qq', label: 'QQ 头像' },
  { value: 'gravatar', label: 'Gravatar' }
] as const

const avatarInputRef = ref<HTMLInputElement | null>(null)

function getLocalizedStr(v: string | Record<string, string> | null | undefined): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

function goBack() {
  router.push('/admin/users')
}

function validatePassword(pwd: string): boolean {
  if (!pwd) return true
  if (pwd.length < 8) return false
  if (!/[a-z]/.test(pwd)) return false
  if (!/[A-Z]/.test(pwd)) return false
  if (!/[0-9]/.test(pwd)) return false
  return true
}

// 老数据可能没有 role，按布尔标记推导
function deriveRole(data: AdminUserRow): string {
  if (data.role && RBAC_ROLES.some(r => r.value === data.role)) return data.role
  if (data.is_superuser) return 'super_admin'
  if (data.is_staff) return 'admin'
  return 'subscriber'
}

async function loadUser() {
  if (!isSuperuser.value) return
  loading.value = true
  loadError.value = false
  loadErrorMsg.value = ''
  try {
    const data = await fetchAdminUserDetail(userId.value)
    user.value = data
    originalTitleId = data.title_id ?? data.title?.id ?? 0
    const initialAvatar = data.resolved_avatar_url ?? data.avatar ?? ''
    originalAvatar = initialAvatar
    Object.assign(form, {
      nickname: data.nickname ?? '',
      email: data.email ?? '',
      website: (data as unknown as { website?: string | null }).website ?? '',
      github: (data as unknown as { github?: string | null }).github ?? '',
      bio: (data as unknown as { bio?: string | null }).bio ?? '',
      avatar: initialAvatar,
      qq: data.qq ?? '',
      avatar_source: data.avatar_source ?? 'auto',
      title_id: originalTitleId,
      role: deriveRole(data),
      is_active: data.is_active,
      is_banned: data.is_banned
    })
  } catch (err) {
    // apiFetch 已自动弹出错误 toast，这里只保留页面级错误态 + 重试入口
    loadError.value = true
    loadErrorMsg.value = err instanceof Error ? err.message : ''
  } finally {
    loading.value = false
  }
}

async function loadTitles() {
  // titles 与用户详情并行拉；即使失败也不阻塞编辑页主体（下拉为空而已）。
  titlesLoading.value = true
  try {
    titles.value = await fetchAdminUserTitles()
  } catch {
    titles.value = []
  } finally {
    titlesLoading.value = false
  }
}

function retryLoad() {
  loadUser()
}

function triggerAvatarUpload() {
  avatarInputRef.value?.click()
}

async function onAvatarFileChange(ev: Event) {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  uploadingAvatar.value = true
  try {
    const res = await useMediaUploadAvatar(file)
    if (res && res.url) {
      // 仅暂存到表单，随「保存」写入目标用户；不能再调 auth.updateAvatar（那是修改当前管理员自己的资料）
      form.avatar = res.url
      toast.success('头像上传成功')
    }
  } catch {
    // apiFetch 已提示错误，无需重复 toast
  } finally {
    uploadingAvatar.value = false
    if (avatarInputRef.value) avatarInputRef.value.value = ''
  }
}

async function saveAll() {
  if (!user.value || saving.value) return
  saveError.value = ''
  if (pwdForm.newPassword) {
    if (!validatePassword(pwdForm.newPassword)) {
      toast.warning('密码需至少 8 位，含大小写字母和数字')
      return
    }
    if (pwdForm.newPassword !== pwdForm.confirmPassword) {
      toast.warning('两次输入的密码不一致')
      return
    }
  }
  saving.value = true
  try {
    // AdminUserUpdateFull 为 extra=forbid（2026-09 起真正生效），字段清单见后端 schema：
    // username/email/nickname/bio/website/github/qq/avatar_source/avatar/cover_image/
    // is_staff/is_active/is_banned/role。title_id 与 is_superuser 不接受（头衔走专用端点，
    // 超管标记由 role 反推），多传即 422。
    const payload: Record<string, unknown> = {
      nickname: form.nickname || null,
      email: form.email,
      website: form.website || null,
      github: form.github || null,
      bio: form.bio || null,
      qq: form.qq.trim() || null,
      avatar_source: form.avatar_source,
      role: form.role,
      is_active: form.is_active,
      is_banned: form.is_banned
    }
    // 载入时 form.avatar 是「解析后」的 URL（可能是 GitHub/QQ/Gravatar 直链）。
    // 未重新上传就回写，会把派生 URL 固化进自定义头像列，此后 auto 解析永远命中它。
    if (form.avatar !== originalAvatar)
      payload.avatar = form.avatar || null
    await updateAdminUserDetail(userId.value, payload)

    // 头衔需单独调用 assign / remove 接口
    const tid = Number(form.title_id) || 0
    if (tid > 0 && tid !== originalTitleId) {
      await assignAdminUserTitle(userId.value, tid)
    } else if (tid <= 0 && originalTitleId > 0) {
      await removeAdminUserTitle(userId.value)
    }

    if (pwdForm.newPassword) {
      await resetAdminUserPassword(userId.value, pwdForm.newPassword)
    }

    toast.success('保存成功')
    router.push('/admin/users')
  } catch (err) {
    // 错误 toast 已由 apiFetch 弹出，这里只保留内联失败提示，避免二次导航
    saveError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!isSuperuser.value || isSelf.value) return
  await Promise.all([loadUser(), loadTitles()])
})
</script>
