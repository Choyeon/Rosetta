<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">
        用户管理
      </h1>
      <Button
        class="bg-gradient-to-r from-primary to-primary/70 hover:from-primary/90 hover:to-primary/60"
        @click="openCreate"
      >
        <Plus class="size-4 mr-2" />
        新建用户
      </Button>
    </div>

    <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
      <div class="relative flex-1 max-w-md">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          v-model="searchQuery"
          placeholder="搜索用户名、邮箱、昵称..."
          class="pl-9"
          @keyup.enter="onSearch"
        />
      </div>
      <Select
        v-model="roleFilter"
        @update:model-value="onFilterChange"
      >
        <SelectTrigger class="w-[140px]">
          <SelectValue placeholder="角色" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">
            全部角色
          </SelectItem>
          <SelectItem value="superuser">
            超级管理员
          </SelectItem>
          <SelectItem value="staff">
            管理员
          </SelectItem>
          <SelectItem value="normal">
            普通用户
          </SelectItem>
        </SelectContent>
      </Select>
      <Select
        v-model="statusFilter"
        @update:model-value="onFilterChange"
      >
        <SelectTrigger class="w-[140px]">
          <SelectValue placeholder="状态" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">
            全部状态
          </SelectItem>
          <SelectItem value="active">
            已激活
          </SelectItem>
          <SelectItem value="inactive">
            未激活
          </SelectItem>
          <SelectItem value="banned">
            已封禁
          </SelectItem>
        </SelectContent>
      </Select>
      <Button
        variant="ghost"
        size="sm"
        @click="onSearch"
      >
        <Search class="size-4 mr-2" />
        搜索
      </Button>
    </div>

    <Card>
      <CardContent class="p-0">
        <div
          v-if="loading"
          class="p-4 space-y-3"
        >
          <div
            v-for="i in 5"
            :key="i"
            class="h-16 rounded-lg"
          >
            <Skeleton class="h-full w-full rounded-lg" />
          </div>
        </div>

        <div
          v-else-if="!filteredUsers.length"
          class="p-16 text-center"
        >
          <Alert
            variant="info"
            class="max-w-md mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>暂无用户</AlertTitle>
            <AlertDescription>当前筛选条件下没有用户数据</AlertDescription>
          </Alert>
        </div>

        <div
          v-else
          class="overflow-x-auto"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b bg-muted/30">
                <th class="text-left font-medium p-4">
                  用户
                </th>
                <th class="text-left font-medium p-4">
                  角色
                </th>
                <th class="text-left font-medium p-4">
                  状态
                </th>
                <th class="text-left font-medium p-4">
                  注册时间
                </th>
                <th class="text-left font-medium p-4">
                  最近登录
                </th>
                <th class="text-left font-medium p-4 text-center">
                  文章/评论
                </th>
                <th class="text-right font-medium p-4">
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(u, i) in filteredUsers"
                :key="u.id"
                :class="i % 2 === 1 ? 'bg-muted/20' : ''"
              >
                <td class="p-4">
                  <div class="flex items-center gap-3">
                    <Avatar class="size-9 shrink-0">
                      <AvatarImage
                        :src="u.resolved_avatar_url ?? ''"
                        :alt="u.username"
                      />
                      <AvatarFallback>{{ u.username?.[0]?.toUpperCase() || 'U' }}</AvatarFallback>
                    </Avatar>
                    <div class="min-w-0">
                      <div class="font-medium truncate">
                        {{ u.nickname || u.username }}
                      </div>
                      <div class="text-xs text-muted-foreground truncate">
                        {{ u.username }} · {{ u.email }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="p-4">
                  <Badge :class="roleBadgeClass(u)">
                    {{ roleText(u) }}
                  </Badge>
                </td>
                <td class="p-4">
                  <div class="flex items-center gap-2">
                    <Badge :class="statusBadgeClass(u)">
                      {{ statusText(u) }}
                    </Badge>
                    <Switch
                      :model-value="u.is_banned"
                      title="封禁/解封"
                      @change="toggleBan(u, $event)"
                    />
                  </div>
                </td>
                <td class="p-4 text-muted-foreground whitespace-nowrap">
                  {{ formatAdminDate(u.created_at) }}
                </td>
                <td class="p-4 text-muted-foreground whitespace-nowrap">
                  {{ formatAdminDateTime(u.last_login) }}
                </td>
                <td class="p-4 text-center">
                  <div class="inline-flex items-center gap-3 text-xs">
                    <span class="inline-flex items-center gap-1">
                      <FileText class="size-3.5 text-muted-foreground" />
                      {{ u.posts_count || 0 }}
                    </span>
                    <span class="inline-flex items-center gap-1">
                      <MessageSquare class="size-3.5 text-muted-foreground" />
                      {{ u.comments_count || 0 }}
                    </span>
                  </div>
                </td>
                <td class="p-4 text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger as="template">
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-8 w-8"
                      >
                        <MoreVertical class="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      class="w-48"
                    >
                      <DropdownMenuItem @click="goEdit(u.id)">
                        <Pencil class="size-4 mr-2" />
                        编辑资料
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        v-if="u.is_superuser || u.is_staff"
                        @click="toggleStaff(u, false)"
                      >
                        <UserX class="size-4 mr-2" />
                        撤销管理员
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        v-else
                        @click="toggleStaff(u, true)"
                      >
                        <UserCheck class="size-4 mr-2" />
                        设为管理员
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        v-if="!u.is_active || u.is_banned"
                        @click="doActivate(u)"
                      >
                        <CheckCircle class="size-4 mr-2" />
                        激活账号
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        v-else
                        @click="doBan(u)"
                      >
                        <Ban class="size-4 mr-2 text-destructive" />
                        <span class="text-destructive">封禁账号</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem @click="openResetPwd(u)">
                        <KeyRound class="size-4 mr-2" />
                        重置密码
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        class="text-destructive focus:text-destructive"
                        @click="openDelete(u)"
                      >
                        <Trash2 class="size-4 mr-2" />
                        删除用户
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>

    <div
      v-if="totalPages > 1"
      class="pt-2"
    >
      <Pagination :items-per-page="pageSize ?? 10">
        <PaginationContent>
          <PaginationItem :value="1" />
          <PaginationPrevious
            :value="1"
            :disabled="page <= 1"
            @click="page > 1 && (page--, fetchData())"
          />
          <template
            v-for="p in visiblePages"
            :key="p"
          >
            <PaginationItem
              v-if="p !== '...'"
              :value="1"
            >
              <Button
                :variant="p === page ? 'default' : 'ghost'"
                size="icon"
                class="h-9 w-9"
                @click="page !== p && (page = p, fetchData())"
              >
                {{ p }}
              </Button>
            </PaginationItem>
            <PaginationItem
              v-else
              :value="1"
            >
              <PaginationEllipsis :value="1" />
            </PaginationItem>
          </template>
          <PaginationItem :value="1" />
          <PaginationNext
            :value="1"
            :disabled="page >= totalPages"
            @click="page < totalPages && (page++, fetchData())"
          />
        </PaginationContent>
      </Pagination>
    </div>

    <Dialog v-model:open="resetPwdDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>重置密码</DialogTitle>
          <DialogDescription>
            为 <span class="font-medium">{{ resetPwdUser?.username }}</span> 设置新密码
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <Label>新密码 <span class="text-destructive">*</span></Label>
            <Input
              v-model="resetPwdForm.newPassword"
              type="password"
              placeholder="至少 8 位，含大小写字母和数字"
            />
            <p class="text-xs text-muted-foreground">
              至少 8 位，需包含大小写字母和数字
            </p>
          </div>
          <div class="space-y-2">
            <Label>确认密码 <span class="text-destructive">*</span></Label>
            <Input
              v-model="resetPwdForm.confirmPassword"
              type="password"
              placeholder="再次输入新密码"
              @keyup.enter="doResetPwd"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="resetPwdDialogOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="resettingPwd"
            @click="doResetPwd"
          >
            <Loader2
              v-if="resettingPwd"
              class="size-4 mr-2 animate-spin"
            />
            确认重置
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认删除用户</DialogTitle>
          <DialogDescription>
            此操作将删除用户 <span class="font-medium text-destructive">{{ deleteUser?.username }}</span> 及其所有引用数据，删除后无法恢复。
          </DialogDescription>
        </DialogHeader>
        <div class="py-2">
          <div class="rounded-xl border bg-error-muted/40 p-4 space-y-3">
            <label class="flex items-start gap-2 cursor-pointer">
              <Checkbox
                v-model="deleteConfirmChecked"
                class="mt-0.5"
              />
              <span class="text-sm">
                我确认删除该用户及其所有引用，此操作不可撤销
              </span>
            </label>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="deleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            :disabled="!deleteConfirmChecked || deleting"
            @click="doDeleteUser"
          >
            <Loader2
              v-if="deleting"
              class="size-4 mr-2 animate-spin"
            />
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="createDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新建用户</DialogTitle>
          <DialogDescription>创建一个新的用户账号</DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <Label>用户名 <span class="text-destructive">*</span></Label>
            <Input
              v-model="createForm.username"
              placeholder="用于登录的用户名"
            />
          </div>
          <div class="space-y-2">
            <Label>邮箱 <span class="text-destructive">*</span></Label>
            <Input
              v-model="createForm.email"
              type="email"
              placeholder="user@example.com"
            />
          </div>
          <div class="space-y-2">
            <Label>昵称</Label>
            <Input
              v-model="createForm.nickname"
              placeholder="显示名称"
            />
          </div>
          <div class="space-y-2">
            <Label>初始密码 <span class="text-destructive">*</span></Label>
            <Input
              v-model="createForm.password"
              type="password"
              placeholder="至少 8 位，含大小写字母和数字"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="createDialogOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="creating"
            @click="doCreate"
          >
            <Loader2
              v-if="creating"
              class="size-4 mr-2 animate-spin"
            />
            创建用户
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '~~/components/ui/dropdown-menu'
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationNext, PaginationPrevious } from '~~/components/ui/pagination'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Checkbox } from '~~/components/ui/checkbox'
import { Label } from '~~/components/ui/label'
import {
  Search, Plus, MoreVertical, Pencil, UserCheck, UserX, CheckCircle, Ban,
  KeyRound, Trash2, Info, Loader2, FileText, MessageSquare
} from '@lucide/vue'
import {
  fetchAdminUsers,
  updateAdminUserFlags,
  activateAdminUser,
  banAdminUser,
  unbanAdminUser,
  resetAdminUserPassword,
  deleteAdminUser,
  formatAdminDate,
  formatAdminDateTime,
  type AdminUserRow
} from '~~/composables/useAdminManage'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()
const router = useRouter()

const loading = ref(false)
const allUsers = ref<AdminUserRow[]>([])
const searchQuery = ref('')
const roleFilter = ref('all')
const statusFilter = ref('all')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const filteredUsers = computed<AdminUserRow[]>(() => {
  let list = [...allUsers.value]
  if (roleFilter.value !== 'all') {
    list = list.filter((u) => {
      if (roleFilter.value === 'superuser') return u.is_superuser
      if (roleFilter.value === 'staff') return u.is_staff && !u.is_superuser
      if (roleFilter.value === 'normal') return !u.is_staff && !u.is_superuser
      return true
    })
  }
  if (statusFilter.value !== 'all') {
    list = list.filter((u) => {
      if (statusFilter.value === 'active') return u.is_active && !u.is_banned
      if (statusFilter.value === 'inactive') return !u.is_active
      if (statusFilter.value === 'banned') return u.is_banned
      return true
    })
  }
  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const visiblePages = computed(() => {
  const tp = totalPages.value
  const curr = page.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  const pages: (number | string)[] = [1]
  if (curr > 3) pages.push('...')
  for (let i = Math.max(2, curr - 1); i <= Math.min(tp - 1, curr + 1); i++) pages.push(i)
  if (curr < tp - 2) pages.push('...')
  pages.push(tp)
  return pages
})

function roleBadgeClass(u: AdminUserRow): string {
  if (u.is_superuser) return 'bg-indigo-100 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300'
  if (u.is_staff) return 'bg-warning-muted text-warning-foreground hover:bg-warning-muted'
  return 'bg-muted text-muted-foreground'
}

function roleText(u: AdminUserRow): string {
  if (u.is_superuser) return '超级管理员'
  if (u.is_staff) return '管理员'
  return '普通用户'
}

function statusBadgeClass(u: AdminUserRow): string {
  if (u.is_banned) return 'bg-destructive/10 text-destructive hover:bg-destructive/10'
  if (u.is_active) return 'bg-success-muted text-success-foreground hover:bg-success-muted'
  return 'bg-muted text-muted-foreground'
}

function statusText(u: AdminUserRow): string {
  if (u.is_banned) return '已封禁'
  if (u.is_active) return '已激活'
  return '未激活'
}

async function fetchData() {
  loading.value = true
  try {
    const res = await fetchAdminUsers({
      page: page.value,
      page_size: pageSize,
      search: searchQuery.value.trim() || undefined
    })
    allUsers.value = res.items ?? []
    total.value = res.total ?? 0
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '加载用户失败')
    allUsers.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  fetchData()
}

function onFilterChange() {
  page.value = 1
}

function goEdit(id: number) {
  router.push(`/admin/users/${id}/edit`)
}

async function toggleStaff(u: AdminUserRow, toStaff: boolean) {
  try {
    await updateAdminUserFlags(u.id, { is_staff: toStaff })
    u.is_staff = toStaff
    toast.success(toStaff ? '已设为管理员' : '已撤销管理员')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '操作失败')
  }
}

async function toggleBan(u: AdminUserRow, ev: unknown) {
  const checked = ev === true || (ev as { checked?: boolean })?.checked === true
  try {
    if (checked) {
      await banAdminUser(u.id)
      u.is_banned = true
      toast.success('已封禁')
    } else {
      await unbanAdminUser(u.id)
      u.is_banned = false
      toast.success('已解封')
    }
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '操作失败')
  }
}

async function doActivate(u: AdminUserRow) {
  try {
    await activateAdminUser(u.id)
    u.is_active = true
    u.is_banned = false
    toast.success('已激活')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '激活失败')
  }
}

async function doBan(u: AdminUserRow) {
  try {
    await banAdminUser(u.id)
    u.is_banned = true
    toast.success('已封禁')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '封禁失败')
  }
}

const resettingPwd = ref(false)
const resetPwdDialogOpen = ref(false)
const resetPwdUser = ref<AdminUserRow | null>(null)
const resetPwdForm = reactive({ newPassword: '', confirmPassword: '' })

function openResetPwd(u: AdminUserRow) {
  resetPwdUser.value = u
  resetPwdForm.newPassword = ''
  resetPwdForm.confirmPassword = ''
  resetPwdDialogOpen.value = true
}

function validatePassword(pwd: string): boolean {
  if (pwd.length < 8) return false
  if (!/[a-z]/.test(pwd)) return false
  if (!/[A-Z]/.test(pwd)) return false
  if (!/[0-9]/.test(pwd)) return false
  return true
}

async function doResetPwd() {
  if (!resetPwdUser.value) return
  if (!validatePassword(resetPwdForm.newPassword)) {
    toast.warning('密码需至少 8 位，含大小写字母和数字')
    return
  }
  if (resetPwdForm.newPassword !== resetPwdForm.confirmPassword) {
    toast.warning('两次输入的密码不一致')
    return
  }
  resettingPwd.value = true
  try {
    await resetAdminUserPassword(resetPwdUser.value.id, resetPwdForm.newPassword)
    toast.success('密码重置成功')
    resetPwdDialogOpen.value = false
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '重置失败')
  } finally {
    resettingPwd.value = false
  }
}

const deleting = ref(false)
const deleteDialogOpen = ref(false)
const deleteUser = ref<AdminUserRow | null>(null)
const deleteConfirmChecked = ref(false)

function openDelete(u: AdminUserRow) {
  deleteUser.value = u
  deleteConfirmChecked.value = false
  deleteDialogOpen.value = true
}

async function doDeleteUser() {
  if (!deleteUser.value) return
  deleting.value = true
  try {
    await deleteAdminUser(deleteUser.value.id)
    toast.success('用户已删除')
    deleteDialogOpen.value = false
    fetchData()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '删除失败')
  } finally {
    deleting.value = false
  }
}

const creating = ref(false)
const createDialogOpen = ref(false)
const createForm = reactive({
  username: '',
  email: '',
  nickname: '',
  password: ''
})

function openCreate() {
  Object.assign(createForm, { username: '', email: '', nickname: '', password: '' })
  createDialogOpen.value = true
}

async function doCreate() {
  if (!createForm.username.trim()) { toast.warning('请输入用户名'); return }
  if (!createForm.email.trim()) { toast.warning('请输入邮箱'); return }
  if (!validatePassword(createForm.password)) { toast.warning('密码不符合要求'); return }
  creating.value = true
  try {
    const apiBase = useRuntimeConfig().public.apiBase as string
    const auth = useAuthStore()
    await $fetch('/users/register', {
      baseURL: apiBase,
      method: 'POST',
      body: {
        username: createForm.username.trim(),
        email: createForm.email.trim(),
        password: createForm.password,
        nickname: createForm.nickname.trim() || undefined
      },
      headers: auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {}
    })
    toast.success('用户创建成功')
    createDialogOpen.value = false
    fetchData()
  } catch (err) {
    const msg = (err as { data?: { message?: string } })?.data?.message
    toast.error(msg || (err instanceof Error ? err.message : '创建失败'))
  } finally {
    creating.value = false
  }
}

onMounted(fetchData)
</script>
