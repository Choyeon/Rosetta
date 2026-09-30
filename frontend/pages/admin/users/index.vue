<!--
  用户管理列表（ssr:false + layout:'admin'）：权限两层隐藏——写端点全是 CurrentSuperUser（staff 只给看列表 +
  只读 banner），后端又禁止管理员操作自己，所以当前登录者那一行既不渲染封禁开关也不给操作菜单。
  角色/状态是"当前这一页"的客户端过滤：改筛选必须重置 page=1 重新拉取，否则停在越界页看似空列表；
  allUsers 用 shallowRef，任何状态变更一律走 patchUser 整行替换（改元素属性不触发重渲染）。
  删除是软删除（封禁 + 停用：评论转匿名、文章仍归属该作者），可用"激活账号"恢复；
  读写一律走 useAdminManage wrapper（失败由 apiFetch 单点 toast，页面只记 loadError 供重试），
  唯一例外是新建用户直连 POST /admin/users——不再借公开注册端点手塞 Bearer，故入口仅超管可见。
-->

<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="用户管理"
      description="查看、编辑与停用注册用户，调整角色权限"
      :icon="Users"
    >
      <template #actions>
        <!-- 创建用户端点 POST /admin/users 为 CurrentSuperUser，对 staff 隐藏避免必吃 403 -->
        <Button
          v-if="isSuperUser"
          size="sm"
          class="rounded-xl shadow-sm"
          @click="openCreate"
        >
          <Plus data-icon="inline-start" />
          新建用户
        </Button>
      </template>
    </AdminPageHeader>

    <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
      <div class="relative flex-1 max-w-md">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          v-model="searchQuery"
          :aria-label="t('admin.users.searchPlaceholder')"
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
        <Search data-icon="inline-start" />
        搜索
      </Button>
    </div>

    <Alert
      v-if="!isSuperUser"
      variant="info"
      class="max-w-none"
    >
      <Info class="size-4" />
      <AlertTitle>只读视图</AlertTitle>
      <AlertDescription>用户的新建、编辑、封禁、角色与删除操作仅限超级管理员，当前账号无权执行。</AlertDescription>
    </Alert>

    <AdminCard>
      <div class="p-0">
        <div
          v-if="loading"
          class="flex flex-col gap-3 p-4"
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
          v-else-if="loadError"
          class="p-16 text-center"
        >
          <Alert
            variant="destructive"
            class="max-w-md mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>加载失败</AlertTitle>
            <AlertDescription>用户列表请求失败，请检查后端状态后重试。</AlertDescription>
            <Button
              variant="outline"
              size="sm"
              class="mt-3"
              @click="fetchData"
            >
              重试
            </Button>
          </Alert>
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
            <caption class="sr-only">
              用户列表：用户名、角色、状态、注册时间、最近登录、头衔与贡献统计
            </caption>
            <thead>
              <tr class="border-b bg-muted/30">
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  用户
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  角色
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  状态
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  注册时间
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  最近登录
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  头衔
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4 text-center"
                >
                  贡献
                </th>
                <th
                  scope="col"
                  class="text-right font-medium p-4"
                >
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
                    <UserAvatar
                      :avatar="u.avatar"
                      :seed="u.username"
                      :name="u.nickname || u.username"
                      :size="36"
                      :show-title="true"
                      :title="u.title || null"
                    />
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
                    <!-- reka-ui 2.10 Switch 受控 prop 是 modelValue，事件是 update:model-value；
                         @change 不会回传布尔值，封禁开关会“拨了不生效” -->
                    <Switch
                      v-if="isSuperUser && u.id !== currentUserId"
                      :model-value="u.is_banned"
                      title="封禁/解封"
                      aria-label="封禁或解封该用户"
                      @update:model-value="toggleBan(u, $event)"
                    />
                  </div>
                </td>
                <td class="p-4 text-muted-foreground whitespace-nowrap">
                  {{ formatAdminDate(u.created_at) }}
                </td>
                <td class="p-4 text-muted-foreground whitespace-nowrap">
                  {{ formatAdminDateTime(u.last_login) }}
                </td>
                <td class="p-4">
                  <div class="inline-flex items-center gap-2">
                    <UserAvatar
                      :avatar="u.avatar"
                      :seed="u.username"
                      :name="u.nickname || u.username"
                      :size="32"
                      :show-title="true"
                      :title="u.title || null"
                    />
                    <span
                      class="text-sm font-medium text-foreground truncate max-w-[120px]"
                      :title="u.nickname || u.username || u.email"
                    >
                      {{ u.nickname || u.username || u.email }}
                    </span>
                  </div>
                </td>
                <td class="p-4 text-center">
                  <div class="inline-flex flex flex-col items-center gap-1">
                    <div class="inline-flex items-center gap-3 text-xs text-muted-foreground">
                      <span class="inline-flex items-center gap-1">
                        <FileText class="size-3.5" />
                        {{ u.posts_count || 0 }}
                      </span>
                      <span class="inline-flex items-center gap-1">
                        <MessageSquare class="size-3.5" />
                        {{ u.comments_count || 0 }}
                      </span>
                    </div>
                  </div>
                </td>
                <td class="p-4 text-right">
                  <!-- 用户管理写端点全部为 CurrentSuperUser；后端亦禁止操作自己，故两者都隐藏入口 -->
                  <span
                    v-if="!isSuperUser || u.id === currentUserId"
                    class="text-muted-foreground"
                  >—</span>
                  <DropdownMenu v-else>
                    <DropdownMenuTrigger as="template">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="用户操作菜单"
                      >
                        <MoreVertical data-icon="inline-start" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      class="w-48"
                    >
                      <DropdownMenuItem @click="goEdit(u.id)">
                        <Pencil data-icon="inline-start" />
                        编辑资料
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <template v-if="!u.is_superuser">
                        <DropdownMenuItem
                          v-if="u.is_staff"
                          @click="toggleStaff(u, false)"
                        >
                          <UserX data-icon="inline-start" />
                          撤销管理员
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          v-else
                          @click="toggleStaff(u, true)"
                        >
                          <UserCheck data-icon="inline-start" />
                          设为管理员
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          v-if="!u.is_active || u.is_banned"
                          @click="doActivate(u)"
                        >
                          <CheckCircle data-icon="inline-start" />
                          激活账号
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          v-else
                          @click="doBan(u)"
                        >
                          <Ban
                            data-icon="inline-start"
                            class="text-destructive"
                          />
                          <span class="text-destructive">封禁账号</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem @click="openResetPwd(u)">
                          <KeyRound data-icon="inline-start" />
                          重置密码
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          class="text-destructive focus:text-destructive"
                          @click="openDelete(u)"
                        >
                          <Trash2 data-icon="inline-start" />
                          删除用户
                        </DropdownMenuItem>
                      </template>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </AdminCard>

    <div class="pt-2">
      <AdminPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-size-options="[10, 20, 50, 100]"
        @update:page="fetchData"
      />
    </div>

    <Dialog v-model:open="resetPwdDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>重置密码</DialogTitle>
          <DialogDescription>
            为 <span class="font-medium">{{ resetPwdUser?.username }}</span> 设置新密码
          </DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 py-2">
          <div class="flex flex-col gap-2">
            <Label for="reset-pwd-new">新密码 <span class="text-destructive">*</span></Label>
            <Input
              id="reset-pwd-new"
              v-model="resetPwdForm.newPassword"
              type="password"
              placeholder="至少 8 位，含大小写字母和数字"
            />
            <p class="text-xs text-muted-foreground">
              至少 8 位，需包含大小写字母和数字
            </p>
          </div>
          <div class="flex flex-col gap-2">
            <Label for="reset-pwd-confirm">确认密码 <span class="text-destructive">*</span></Label>
            <Input
              id="reset-pwd-confirm"
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
              data-icon="inline-start"
              class="animate-spin"
            />
            确认重置
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 破坏性删除统一走 DangerConfirmDialog：需输入确认短语，失败内联展示并保持弹窗可重试 -->
    <DangerConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除用户"
      confirm-text="确认删除"
      confirm-phrase="删除用户"
      phrase-hint="请输入：删除用户"
      :on-confirm="doDeleteUser"
    >
      <template #description>
        此操作将删除用户
        <span class="font-medium text-destructive">{{ deleteUser?.username }}</span>
        ——后端执行软删除（封禁 + 停用，账号数据保留，可用"激活"恢复）。
        该用户的评论与留言板发言会变为匿名，文章仍归属该作者且不会被删除。
      </template>
    </DangerConfirmDialog>

    <Dialog v-model:open="createDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新建用户</DialogTitle>
          <DialogDescription>创建一个新的用户账号</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 py-2">
          <div class="flex flex-col gap-2">
            <Label for="create-user-username">用户名 <span class="text-destructive">*</span></Label>
            <Input
              id="create-user-username"
              v-model="createForm.username"
              placeholder="3-150 位字母、数字、下划线或连字符"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="create-user-email">邮箱 <span class="text-destructive">*</span></Label>
            <Input
              id="create-user-email"
              v-model="createForm.email"
              type="email"
              placeholder="user@example.com"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="create-user-nickname">昵称</Label>
            <Input
              id="create-user-nickname"
              v-model="createForm.nickname"
              placeholder="显示名称"
            />
          </div>
          <div class="flex flex-col gap-2">
            <Label for="create-user-password">初始密码 <span class="text-destructive">*</span></Label>
            <Input
              id="create-user-password"
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
              data-icon="inline-start"
              class="animate-spin"
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
 
import AdminCard from '~~/components/admin/AdminCard.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import UserAvatar from '~~/components/UserAvatar.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '~~/components/ui/dropdown-menu'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { apiFetch } from '~~/composables/useApi'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Label } from '~~/components/ui/label'
import { useI18n } from 'vue-i18n'
import {
  Search, Plus, MoreVertical, Pencil, UserCheck, UserX, CheckCircle, Ban,
  KeyRound, Trash2, Info, Loader2, FileText, MessageSquare,
  Users
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
  type AdminUserQuery,
  type AdminUserRow
} from '~~/composables/useAdminManage'

definePageMeta({ ssr: false, layout: 'admin' })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()
const auth = useAuthStore()

// 后端 /api/admin/users* 全部写端点为 CurrentSuperUser（users.py 列表仅 CurrentStaff）：
// staff 只给看列表，所有操作入口隐藏，避免点击只吃 403。
const isSuperUser = computed(() => auth.user?.is_superuser === true)
// 后端禁止管理员对自己执行改状态/封禁/重置/删除（400），自己的行不提供入口。
const currentUserId = computed(() => auth.user?.id ?? null)

const loading = ref(false)
const loadError = ref(false)
// shallowRef：用户列表整赋值替换，避免深层响应式开销
const allUsers = shallowRef<AdminUserRow[]>([])
const searchQuery = ref('')
const roleFilter = ref('all')
const statusFilter = ref('all')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

/**
 * 状态（激活 / 未激活 / 封禁）筛到服务端去了：`GET /api/admin/users` 原生支持
 * is_active / is_banned，只有交给后端才能拿到正确的 total 与分页。
 * 此前全部在客户端切「当前页的 20 行」，于是「已封禁」这一档永远筛不出东西
 * （列表接口当时压根不返回 is_banned），而且 total 显示的是未过滤的总数。
 *
 * 角色筛选仍在客户端：后端只有 is_staff 一个布尔，没有「超级管理员 / 管理员 / 普通」
 * 三档参数，为它加一个枚举参数会让列表端点背上前端的展示语义，不划算。
 * 代价是角色筛选只作用于当前页，这是已知取舍，不是 bug。
 */
const filteredUsers = computed<AdminUserRow[]>(() => {
  if (roleFilter.value === 'all') return allUsers.value
  return allUsers.value.filter((u) => {
    if (roleFilter.value === 'superuser') return u.is_superuser
    if (roleFilter.value === 'staff') return u.is_staff && !u.is_superuser
    if (roleFilter.value === 'normal') return !u.is_staff && !u.is_superuser
    return true
  })
})

/** 状态筛选 → 后端查询参数。三档互斥，未选时为 undefined（= 不过滤）。 */
function statusQuery(): Pick<AdminUserQuery, 'is_active' | 'is_banned'> {
  if (statusFilter.value === 'active') return { is_active: true, is_banned: false }
  if (statusFilter.value === 'inactive') return { is_active: false }
  if (statusFilter.value === 'banned') return { is_banned: true }
  return {}
}

function roleBadgeClass(u: AdminUserRow): string {
  if (u.is_superuser) return 'bg-indigo-100 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300'
  if (u.is_staff) return 'bg-warning-muted text-warning-muted-foreground hover:bg-warning-muted'
  return 'bg-muted text-muted-foreground'
}

function roleText(u: AdminUserRow): string {
  if (u.is_superuser) return '超级管理员'
  if (u.is_staff) return '管理员'
  return '普通用户'
}

function statusBadgeClass(u: AdminUserRow): string {
  if (u.is_banned) return 'bg-destructive/10 text-destructive hover:bg-destructive/10'
  if (u.is_active) return 'bg-success-muted text-success-muted-foreground hover:bg-success-muted'
  return 'bg-muted text-muted-foreground'
}

function statusText(u: AdminUserRow): string {
  if (u.is_banned) return '已封禁'
  if (u.is_active) return '已激活'
  return '未激活'
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const res = await fetchAdminUsers({
      page: page.value,
      page_size: pageSize.value,
      search: searchQuery.value.trim() || undefined,
      ...statusQuery()
    })
    let items = res.items ?? []
    total.value = res.total ?? 0
    // 删除/封禁后回到越界空页：自动回退一页，避免停在"第 N 页无数据"的假空态
    if (items.length === 0 && total.value > 0 && page.value > 1) {
      page.value -= 1
      loading.value = false
      await fetchData()
      return
    }
    allUsers.value = items
  } catch {
    // apiFetch 已统一 toast（fetchAdminUsers 内部），页面只记录错误态供重试，不再重复弹
    allUsers.value = []
    total.value = 0
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  fetchData()
}

function onFilterChange() {
  // 角色/状态是客户端对"当前页"数据的过滤：切换筛选必须回到第 1 页并重新拉取，
  // 否则会出现"停在第 N 页 + 客户端过滤后看起来没有数据"的错位。
  page.value = 1
  fetchData()
}

function goEdit(id: number) {
  router.push(`/admin/users/${id}/edit`)
}

// allUsers 是 shallowRef：直接改元素属性不会触发重渲染，
// 统一用"整行替换"的方式把最新状态写回列表。
function patchUser(id: number, patch: Partial<AdminUserRow>) {
  allUsers.value = allUsers.value.map((u) => (u.id === id ? { ...u, ...patch } : u))
}

async function toggleStaff(u: AdminUserRow, toStaff: boolean) {
  try {
    await updateAdminUserFlags(u.id, { is_staff: toStaff })
    patchUser(u.id, { is_staff: toStaff })
    toast.success(toStaff ? '已设为管理员' : '已撤销管理员')
  } catch {
    // apiFetch 已自动 toast，避免双报；失败时不改本地行
  }
}

async function toggleBan(u: AdminUserRow, value: unknown) {
  const checked = value === true
  try {
    if (checked) {
      await banAdminUser(u.id)
      patchUser(u.id, { is_banned: true })
      toast.success('已封禁')
    } else {
      await unbanAdminUser(u.id)
      patchUser(u.id, { is_banned: false })
      toast.success('已解封')
    }
  } catch {
    // apiFetch 已自动 toast；开关保持原值（受控 model-value 未变）
  }
}

async function doActivate(u: AdminUserRow) {
  try {
    await activateAdminUser(u.id)
    patchUser(u.id, { is_active: true, is_banned: false })
    toast.success('已激活')
  } catch {
    // apiFetch 已自动 toast
  }
}

async function doBan(u: AdminUserRow) {
  try {
    await banAdminUser(u.id)
    patchUser(u.id, { is_banned: true })
    toast.success('已封禁')
  } catch {
    // apiFetch 已自动 toast
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
  } catch {
    // apiFetch 已自动 toast（唯一报错点）；弹窗保持打开供修正
  } finally {
    resettingPwd.value = false
  }
}

const deleteDialogOpen = ref(false)
const deleteUser = ref<AdminUserRow | null>(null)

function openDelete(u: AdminUserRow) {
  deleteUser.value = u
  deleteDialogOpen.value = true
}

/** DangerConfirmDialog 的 onConfirm：throw 即由弹窗内联展示错误并保持可重试 */
async function doDeleteUser() {
  if (!deleteUser.value) return
  await deleteAdminUser(deleteUser.value.id)
  toast.success('用户已删除（账号已封禁停用）')
  deleteUser.value = null
  await fetchData()
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
  // 与后端 AdminUserCreate 契约对齐：username 3-150 且仅 [a-zA-Z0-9_-]，
  // 密码 ≥8 位含大小写与数字（validatePassword 同规则），先在前端拦一道给出人话提示。
  if (!createForm.username.trim()) { toast.warning('请输入用户名'); return }
  if (!/^[a-zA-Z0-9_-]{3,150}$/.test(createForm.username.trim())) {
    toast.warning('用户名需 3-150 位，仅允许字母、数字、下划线和连字符')
    return
  }
  if (!createForm.email.trim()) { toast.warning('请输入邮箱'); return }
  if (!validatePassword(createForm.password)) { toast.warning('密码需至少 8 位，含大小写字母和数字'); return }
  creating.value = true
  try {
    // 走 apiFetch + staff 专用端点 POST /admin/users（backend/api/admin.py admin_create_user），
    // 不再借用公开注册端点 /users/register 手动塞 Bearer；401 刷新与错误契约由 apiFetch 统一处理。
    // apiFetch 失败已自动 toast（唯一报错点），这里只中断流程、不重复弹。
    await apiFetch('/admin/users', {
      method: 'POST',
      body: {
        username: createForm.username.trim(),
        email: createForm.email.trim(),
        password: createForm.password,
        nickname: createForm.nickname.trim() || undefined
      }
    })
    toast.success('用户创建成功')
    createDialogOpen.value = false
    fetchData()
  } catch {
    // 错误提示已由 apiFetch 统一 toast，此处保持对话框打开供用户修正
  } finally {
    creating.value = false
  }
}

onMounted(fetchData)
</script>
