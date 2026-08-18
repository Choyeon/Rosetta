<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          class="h-9 w-9"
          @click="goBack"
        >
          <ArrowLeft class="size-5" />
        </Button>
        <h1 class="text-2xl font-bold">
          编辑用户
        </h1>
      </div>
    </div>

    <div
      v-if="loading"
      class="grid grid-cols-1 lg:grid-cols-2 gap-6"
    >
      <Card>
        <CardContent class="p-6 space-y-6">
          <div class="flex items-center gap-4">
            <Skeleton class="size-20 rounded-full" />
            <Skeleton class="h-9 w-28 rounded-lg" />
          </div>
          <div class="space-y-4">
            <Skeleton class="h-10 w-full rounded-lg" />
            <Skeleton class="h-10 w-full rounded-lg" />
            <Skeleton class="h-10 w-full rounded-lg" />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-6 space-y-6">
          <Skeleton class="h-20 w-full rounded-lg" />
          <Skeleton class="h-20 w-full rounded-lg" />
        </CardContent>
      </Card>
    </div>

    <template v-else>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <User class="size-5 text-muted-foreground" />
              基本资料
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-6">
            <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <Avatar class="size-20 shrink-0 border-4 border-muted">
                <AvatarImage
                  :src="form.avatar ?? ''"
                  :alt="form.nickname || form.username"
                />
                <AvatarFallback class="text-2xl">
                  {{ (form.nickname || form.username)?.[0]?.toUpperCase() || 'U' }}
                </AvatarFallback>
              </Avatar>
              <div class="space-y-2">
                <Button
                  variant="outline"
                  size="sm"
                  @click="triggerAvatarUpload"
                >
                  <Upload class="size-4 mr-2" />
                  上传头像
                </Button>
                <p class="text-xs text-muted-foreground">
                  上传到 /media/avatar
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

            <div class="space-y-4">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-2">
                  <Label>昵称</Label>
                  <Input
                    v-model="form.nickname"
                    placeholder="显示名称"
                  />
                </div>
                <div class="space-y-2">
                  <Label>邮箱</Label>
                  <Input
                    v-model="form.email"
                    type="email"
                    placeholder="user@example.com"
                  />
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div class="space-y-2">
                  <Label>个人网站</Label>
                  <Input
                    v-model="form.website"
                    placeholder="https://..."
                  />
                </div>
                <div class="space-y-2">
                  <Label>GitHub</Label>
                  <Input
                    v-model="form.github"
                    placeholder="github.com/username"
                  />
                </div>
                <div class="space-y-2">
                  <Label>QQ</Label>
                  <Input
                    v-model="form.qq"
                    placeholder="QQ 号码"
                  />
                </div>
              </div>
              <div class="space-y-2">
                <Label>自我介绍</Label>
                <Textarea
                  v-model="form.bio"
                  rows="4"
                  placeholder="介绍一下这个用户..."
                  class="resize-none"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <Shield class="size-5 text-muted-foreground" />
              账号安全
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-6">
            <div class="space-y-3">
              <div class="text-sm font-medium">
                角色权限
              </div>
              <div class="space-y-3">
                <div class="flex items-center justify-between rounded-xl border p-3">
                  <div>
                    <div class="text-sm font-medium">
                      管理员（Staff）
                    </div>
                    <div class="text-xs text-muted-foreground">
                      可进入管理后台
                    </div>
                  </div>
                  <Switch
                    v-model="form.is_staff"
                    :disabled="!isSuperuser"
                  />
                </div>
                <div class="flex items-center justify-between rounded-xl border p-3">
                  <div>
                    <div class="text-sm font-medium">
                      超级管理员（Superuser）
                    </div>
                    <div class="text-xs text-muted-foreground">
                      拥有所有权限
                    </div>
                  </div>
                  <Switch
                    v-model="form.is_superuser"
                    :disabled="!isSuperuser"
                  />
                </div>
              </div>
              <p
                v-if="!isSuperuser"
                class="text-xs text-muted-foreground"
              >
                仅超级管理员可修改角色设置
              </p>
            </div>

            <Separator />

            <div class="space-y-3">
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
                  <Switch v-model="form.is_active" />
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
                  <Switch v-model="form.is_banned" />
                </div>
              </div>
            </div>

            <Separator />

            <div class="space-y-3">
              <div class="text-sm font-medium">
                修改密码
              </div>
              <div class="space-y-3">
                <div class="space-y-2">
                  <Label>新密码</Label>
                  <Input
                    v-model="pwdForm.newPassword"
                    type="password"
                    placeholder="留空则不修改"
                  />
                  <p class="text-xs text-muted-foreground">
                    至少 8 位，含大小写字母和数字
                  </p>
                </div>
                <div class="space-y-2">
                  <Label>确认密码</Label>
                  <Input
                    v-model="pwdForm.confirmPassword"
                    type="password"
                    placeholder="再次输入新密码"
                  />
                </div>
              </div>
            </div>

            <Separator />

            <div class="space-y-2">
              <Label>头衔</Label>
              <Select
                v-model="form.title_id"
                :disabled="titlesLoading"
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择头衔" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem :value="0">
                    无
                  </SelectItem>
                  <SelectItem
                    v-for="t in titles"
                    :key="t.id"
                    :value="t.id"
                  >
                    <span class="inline-flex items-center gap-2">
                      <span>{{ t.icon || '🏷' }}</span>
                      <span>{{ t.name }}</span>
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>

      <div class="flex justify-end gap-3 pt-4">
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
            class="size-4 mr-2 animate-spin"
          />
          保存更改
        </Button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Switch } from '~~/components/ui/switch'
import { Separator } from '~~/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Label } from '~~/components/ui/label'
import { Skeleton } from '~~/components/ui/skeleton'
import {
  ArrowLeft, User, Shield, Upload, Loader2
} from '@lucide/vue'
import {
  fetchAdminUserDetail,
  updateAdminUserDetail,
  fetchAdminUserTitles,
  resetAdminUserPassword,
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
  if (Array.isArray(raw)) return parseInt(raw[0], 10)
  return parseInt(raw as string, 10)
})

const isSuperuser = computed(() => auth.user?.is_superuser === true)

const loading = ref(false)
const saving = ref(false)
const titlesLoading = ref(false)

const user = ref<AdminUserRow | null>(null)
const titles = ref<AdminUserTitle[]>([])

const form = reactive({
  nickname: '' as string | null,
  email: '',
  website: '' as string | null,
  github: '' as string | null,
  qq: '' as string | null,
  bio: '' as string | null,
  avatar: '' as string | null,
  title_id: 0 as number,
  is_staff: false,
  is_superuser: false,
  is_active: false,
  is_banned: false
})

const pwdForm = reactive({
  newPassword: '',
  confirmPassword: ''
})

const avatarInputRef = ref<HTMLInputElement | null>(null)

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

async function loadUser() {
  loading.value = true
  try {
    const data = await fetchAdminUserDetail(userId.value)
    user.value = data
    Object.assign(form, {
      nickname: data.nickname ?? '',
      email: data.email ?? '',
      website: (data as unknown as { website?: string | null }).website ?? '',
      github: (data as unknown as { github?: string | null }).github ?? '',
      qq: (data as unknown as { qq?: string | null }).qq ?? '',
      bio: (data as unknown as { bio?: string | null }).bio ?? '',
      avatar: data.resolved_avatar_url ?? data.avatar ?? '',
      title_id: (data as unknown as { title_id?: number }).title_id ?? 0,
      is_staff: data.is_staff,
      is_superuser: data.is_superuser,
      is_active: data.is_active,
      is_banned: data.is_banned
    })
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '加载用户详情失败')
  } finally {
    loading.value = false
  }
}

async function loadTitles() {
  titlesLoading.value = true
  try {
    titles.value = await fetchAdminUserTitles()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '加载头衔失败')
    titles.value = []
  } finally {
    titlesLoading.value = false
  }
}

function triggerAvatarUpload() {
  avatarInputRef.value?.click()
}

async function onAvatarFileChange(ev: Event) {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  try {
    const res = await useMediaUploadAvatar(file)
    if (res && res.url) {
      form.avatar = res.url
      auth.updateAvatar(res.url)
      toast.success('头像上传成功')
    }
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '头像上传失败')
  } finally {
    if (avatarInputRef.value) avatarInputRef.value.value = ''
  }
}

async function saveAll() {
  if (!user.value) return
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
    const payload: Record<string, unknown> = {
      nickname: form.nickname || null,
      email: form.email,
      website: form.website || null,
      github: form.github || null,
      qq: form.qq || null,
      bio: form.bio || null,
      avatar: form.avatar || null,
      title_id: form.title_id || null,
      is_staff: form.is_staff,
      is_superuser: form.is_superuser,
      is_active: form.is_active,
      is_banned: form.is_banned
    }
    await updateAdminUserDetail(userId.value, payload)

    if (pwdForm.newPassword) {
      await resetAdminUserPassword(userId.value, pwdForm.newPassword)
    }

    toast.success('保存成功')
    router.push('/admin/users')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadUser(), loadTitles()])
})
</script>
