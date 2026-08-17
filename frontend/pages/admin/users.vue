<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-3xl font-bold tracking-tight font-display">
          {{ t('admin.users.title') }}
        </h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ t('admin.users.desc') }}
        </p>
      </div>
      <div class="flex items-center gap-2 w-full sm:w-80">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            v-model="search"
            :placeholder="t('admin.users.searchPlaceholder')"
            class="pl-9"
            @keyup.enter="onSearch"
          />
        </div>
        <Button
          variant="secondary"
          @click="onSearch"
        >
          {{ t('admin.users.search') }}
        </Button>
      </div>
    </div>

    <!-- 错误重试 -->
    <div
      v-if="loadError"
      class="flex flex-col items-start gap-3"
    >
      <Alert variant="destructive">
        <AlertCircle class="size-4" />
        <AlertTitle>{{ t('admin.users.loadFailed') }}</AlertTitle>
        <AlertDescription>{{ loadError }}</AlertDescription>
      </Alert>
      <Button
        variant="outline"
        size="sm"
        :disabled="loading"
        @click="load"
      >
        <RefreshCw
          class="mr-2 size-4"
          :class="{ 'animate-spin': loading }"
        />
        {{ t('admin.users.retry') }}
      </Button>
    </div>

    <Card v-else>
      <CardContent class="p-0">
        <div
          v-if="loading && users.length === 0"
          class="p-4 space-y-3"
        >
          <Skeleton
            v-for="i in 6"
            :key="i"
            class="h-14 w-full"
          />
        </div>

        <div
          v-else-if="users.length > 0"
          class="overflow-x-auto"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b">
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.users.thUser') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.users.thRole') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.users.thStatus') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.users.thRegistered') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.users.thLastActive') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.users.thCounts') }}
                </th>
                <th class="text-right font-medium text-muted-foreground p-3">
                  {{ t('admin.users.thActions') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="u in users"
                :key="u.id"
                class="border-b last:border-0 transition-colors hover:bg-muted/50"
              >
                <td class="p-3">
                  <div class="flex items-center gap-2">
                    <Avatar size="sm">
                      <AvatarImage
                        v-if="u.resolved_avatar_url ?? u.avatar"
                        :src="u.resolved_avatar_url ?? u.avatar ?? ''"
                        :alt="u.nickname ?? u.username"
                      />
                      <AvatarFallback>{{ (u.nickname ?? u.username)[0] }}</AvatarFallback>
                    </Avatar>
                    <div class="min-w-0">
                      <p class="font-medium truncate">
                        {{ u.nickname ?? u.username }}
                        <span
                          v-if="u.id === currentUserId"
                          class="text-xs text-muted-foreground"
                        >
                          ({{ t('admin.users.self') }})
                        </span>
                      </p>
                      <p class="text-xs text-muted-foreground truncate">
                        {{ u.username }} · {{ u.email }}
                      </p>
                    </div>
                  </div>
                </td>
                <td class="p-3">
                  <Badge :class="roleBadgeClass(u)">
                    {{ roleLabel(u) }}
                  </Badge>
                </td>
                <td class="p-3">
                  <Badge :class="userStatusBadgeClass(u)">
                    {{ userStatusLabel(u) }}
                  </Badge>
                </td>
                <td class="p-3 text-muted-foreground whitespace-nowrap">
                  {{ formatAdminDate(u.created_at) }}
                </td>
                <td class="p-3 text-muted-foreground whitespace-nowrap">
                  {{ formatAdminDateTime(u.last_login) }}
                </td>
                <td class="p-3 text-muted-foreground whitespace-nowrap">
                  {{ t('admin.users.postsCount', { n: u.posts_count }) }} /
                  {{ t('admin.users.commentsCount', { n: u.comments_count }) }}
                </td>
                <td class="p-3 text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger as-child>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        class="size-8"
                        :disabled="!canOperate(u)"
                      >
                        <MoreHorizontal class="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      class="w-52"
                    >
                      <DropdownMenuItem
                        :disabled="actionLoading"
                        @select.prevent="onToggleStaff(u)"
                      >
                        <UserCog class="mr-2 size-4" />
                        <span>{{ u.is_staff ? t('admin.users.makeMember') : t('admin.users.makeStaff') }}</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        v-if="u.is_banned || !u.is_active"
                        :disabled="actionLoading"
                        @select.prevent="onActivate(u)"
                      >
                        <UserCheck class="mr-2 size-4" />
                        <span>{{ t('admin.users.activate') }}</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        v-else
                        :disabled="actionLoading"
                        @select.prevent="onBan(u)"
                      >
                        <UserX class="mr-2 size-4" />
                        <span>{{ t('admin.users.disable') }}</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        :disabled="actionLoading"
                        @select.prevent="openResetPassword(u)"
                      >
                        <KeyRound class="mr-2 size-4" />
                        <span>{{ t('admin.users.resetPassword') }}</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        class="text-destructive focus:text-destructive"
                        :disabled="actionLoading"
                        @select.prevent="pendingDelete = u"
                      >
                        <Trash2 class="mr-2 size-4" />
                        <span>{{ t('admin.users.delete') }}</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div
          v-else
          class="flex flex-col items-center justify-center py-16 text-muted-foreground"
        >
          <UsersIcon class="size-8 mb-2" />
          <p class="text-sm">
            {{ t('admin.users.empty') }}
          </p>
        </div>
      </CardContent>
    </Card>

    <!-- 分页 -->
    <div
      v-if="totalPages > 1"
      class="flex justify-center"
    >
      <Pagination
        v-slot="{ page }"
        :page="currentPage"
        :total="total"
        :items-per-page="pageSize"
        :sibling-count="1"
        show-edges
        @update:page="onPageChange"
      >
        <PaginationContent v-slot="{ items }">
          <PaginationPrevious />
          <template
            v-for="(item, index) in items"
            :key="index"
          >
            <PaginationListItem
              v-if="item.type === 'page'"
              :value="item.value"
              :is-active="item.value === page"
            >
              {{ item.value }}
            </PaginationListItem>
            <PaginationEllipsis v-else />
          </template>
          <PaginationNext />
        </PaginationContent>
      </Pagination>
    </div>

    <!-- 重置密码 Dialog -->
    <Dialog
      :open="resetTarget !== null"
      @update:open="(v: boolean) => { if (!v) resetTarget = null }"
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('admin.users.resetPasswordTitle') }}</DialogTitle>
          <DialogDescription>
            {{ t('admin.users.resetPasswordDesc', { name: resetTarget?.nickname ?? resetTarget?.username ?? '' }) }}
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-2">
          <Input
            v-model="newPassword"
            type="password"
            :placeholder="t('admin.users.newPasswordPlaceholder')"
          />
          <p class="text-xs text-muted-foreground">
            {{ t('admin.users.passwordHint') }}
          </p>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="resetTarget = null"
          >
            {{ t('admin.users.cancel') }}
          </Button>
          <Button
            :disabled="actionLoading"
            @click="confirmResetPassword"
          >
            {{ t('admin.users.confirmReset') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 删除确认 Dialog -->
    <Dialog
      :open="pendingDelete !== null"
      @update:open="(v: boolean) => { if (!v) pendingDelete = null }"
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('admin.users.deleteTitle') }}</DialogTitle>
          <DialogDescription>
            {{ t('admin.users.deleteDesc', { name: pendingDelete?.nickname ?? pendingDelete?.username ?? '' }) }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            @click="pendingDelete = null"
          >
            {{ t('admin.users.cancel') }}
          </Button>
          <Button
            variant="destructive"
            :disabled="actionLoading"
            @click="confirmDelete"
          >
            {{ t('admin.users.confirmDelete') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Input } from '~~/components/ui/input'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationListItem,
  PaginationNext,
  PaginationPrevious
} from '~~/components/ui/pagination'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '~~/components/ui/dropdown-menu'
import {
  Alert,
  AlertDescription,
  AlertTitle
} from '~~/components/ui/alert'
import {
  Search,
  RefreshCw,
  AlertCircle,
  MoreHorizontal,
  UserCog,
  UserCheck,
  UserX,
  KeyRound,
  Trash2,
  Users as UsersIcon
} from '@lucide/vue'
import { useAuthStore } from '~~/stores/auth'
import {
  activateAdminUser,
  banAdminUser,
  deleteAdminUser,
  fetchAdminUsers,
  formatAdminDate,
  formatAdminDateTime,
  resetAdminUserPassword,
  updateAdminUserFlags,
  type AdminUserRow
} from '~~/composables/useAdminManage'

definePageMeta({
  layout: 'admin'
})

const { t } = useI18n()
const toast = useToast()
const authStore = useAuthStore()

const currentUserId = computed(() => authStore.user?.id ?? -1)

const search = ref('')
const currentPage = ref(1)
const pageSize = 20

const users = ref<AdminUserRow[]>([])
const total = ref(0)
const totalPages = ref(0)
const loading = ref(false)
const loadError = ref('')
const actionLoading = ref(false)

const pendingDelete = ref<AdminUserRow | null>(null)
const resetTarget = ref<AdminUserRow | null>(null)
const newPassword = ref('')

function canOperate(u: AdminUserRow): boolean {
  return !u.is_superuser && u.id !== currentUserId.value
}

function roleLabel(u: AdminUserRow): string {
  if (u.is_superuser) return t('admin.users.roleAdmin')
  if (u.is_staff) return t('admin.users.roleStaff')
  return t('admin.users.roleUser')
}

function roleBadgeClass(u: AdminUserRow): string {
  if (u.is_superuser) return 'bg-error-muted text-error border-transparent'
  if (u.is_staff) return 'bg-info-muted text-info border-transparent'
  return 'bg-muted text-muted-foreground border-transparent'
}

function userStatusLabel(u: AdminUserRow): string {
  if (u.is_banned) return t('admin.users.statusBanned')
  if (!u.is_active) return t('admin.users.statusInactive')
  return t('admin.users.statusActive')
}

function userStatusBadgeClass(u: AdminUserRow): string {
  if (u.is_banned) return 'bg-error-muted text-error border-transparent'
  if (!u.is_active) return 'bg-warning-muted text-warning border-transparent'
  return 'bg-success-muted text-success border-transparent'
}

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchAdminUsers({
      page: currentPage.value,
      page_size: pageSize,
      search: search.value
    })
    users.value = res.items
    total.value = res.total
    totalPages.value = res.total_pages
  } catch (err) {
    const e = err as { data?: { message?: string, detail?: unknown } }
    loadError.value = e?.data?.message
      ?? (typeof e?.data?.detail === 'string' ? e.data.detail : '')
      || (err instanceof Error ? err.message : String(err))
  } finally {
    loading.value = false
  }
}

function onSearch(): void {
  currentPage.value = 1
  load()
}

function onPageChange(p: number): void {
  currentPage.value = p
  load()
}

async function onToggleStaff(u: AdminUserRow): Promise<void> {
  actionLoading.value = true
  try {
    await updateAdminUserFlags(u.id, { is_staff: !u.is_staff })
    toast.success(u.is_staff ? t('admin.users.toast.madeMember') : t('admin.users.toast.madeStaff'))
    await load()
  } catch {
    // apiFetch 已 toast
  } finally {
    actionLoading.value = false
  }
}

async function onBan(u: AdminUserRow): Promise<void> {
  actionLoading.value = true
  try {
    const res = await banAdminUser(u.id)
    toast.success(res.message ?? t('admin.users.toast.banned'))
    await load()
  } catch {
    // ignore
  } finally {
    actionLoading.value = false
  }
}

async function onActivate(u: AdminUserRow): Promise<void> {
  actionLoading.value = true
  try {
    const res = await activateAdminUser(u.id)
    toast.success(res.message ?? t('admin.users.toast.activated'))
    await load()
  } catch {
    // ignore
  } finally {
    actionLoading.value = false
  }
}

function openResetPassword(u: AdminUserRow): void {
  resetTarget.value = u
  newPassword.value = ''
}

function validPassword(pw: string): boolean {
  return pw.length >= 8 && /[a-z]/.test(pw) && /[A-Z]/.test(pw) && /\d/.test(pw)
}

async function confirmResetPassword(): Promise<void> {
  if (!resetTarget.value) return
  if (!validPassword(newPassword.value)) {
    toast.warning(t('admin.users.passwordHint'))
    return
  }
  actionLoading.value = true
  try {
    const res = await resetAdminUserPassword(resetTarget.value.id, newPassword.value)
    toast.success(res.message ?? t('admin.users.toast.passwordReset'))
    resetTarget.value = null
    newPassword.value = ''
  } catch {
    // ignore
  } finally {
    actionLoading.value = false
  }
}

async function confirmDelete(): Promise<void> {
  if (!pendingDelete.value) return
  actionLoading.value = true
  try {
    const res = await deleteAdminUser(pendingDelete.value.id)
    toast.success(res.message ?? t('admin.users.toast.deleted'))
    pendingDelete.value = null
    await load()
  } catch {
    // ignore
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  load()
})
</script>
