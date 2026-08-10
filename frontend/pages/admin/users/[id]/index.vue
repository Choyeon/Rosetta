<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
const toast = useToast();
const route = useRoute();
const router = useRouter();

const userId = computed(() => route.params.id as string);
useHead({ title: `用户详情 #${userId.value} - Rosetta 后台` });

const saving = ref(false);
const resetting = ref(false);

const { data: user, pending, refresh } = await useFetch<any>(() => `/api/admin/users/${userId.value}`, {
  default: () => ({
    id: 0,
    username: "",
    nickname: "",
    email: "",
    avatar: "",
    bio: "",
    roles: ["viewer"] as string[],
    active: true,
    createdAt: "",
    updatedAt: "",
    lastLoginAt: "",
    lastLoginIp: "",
    loginCount: 0,
    postsCount: 0,
    commentsCount: 0,
    dynamicsCount: 0,
    website: "",
    github: "",
    twitter: "",
    location: "",
    activities: [] as any[],
  }),
  lazy: true,
  server: false,
});

const editing = ref<any>(null);
const editOpen = ref(false);

const resetDialog = ref(false);
const newPassword = ref("");
const confirmPassword = ref("");

const roleOptions = [
  { value: "super_admin", label: "超级管理员", color: "danger" },
  { value: "admin", label: "管理员", color: "primary" },
  { value: "editor", label: "编辑", color: "info" },
  { value: "author", label: "作者", color: "success" },
  { value: "contributor", label: "投稿者", color: "warning" },
  { value: "viewer", label: "订阅者", color: "neutral" },
  { value: "guest", label: "访客", color: "neutral" },
  { value: "user", label: "用户", color: "neutral" },
];

function getRoleMeta(role: string) {
  return roleOptions.find(r => r.value === role) || { label: role, color: "neutral" };
}

function openEdit() {
  if (!user.value) return;
  editing.value = structuredClone(user.value);
  editOpen.value = true;
}

async function saveEdit() {
  if (!editing.value) return;
  saving.value = true;
  try {
    await apiPut(`/api/admin/users/${editing.value.id}`, {
      nickname: editing.value.nickname,
      email: editing.value.email,
      bio: editing.value.bio,
      website: editing.value.website,
      github: editing.value.github,
      twitter: editing.value.twitter,
      location: editing.value.location,
      roles: editing.value.roles,
      active: editing.value.active,
    });
    toast.add({ title: "保存成功", color: "success" });
    editOpen.value = false;
    editing.value = null;
    await refresh();
  } catch (err: any) {
    toast.add({ title: "保存失败", description: err?.message || "保存失败", color: "danger" });
  } finally {
    saving.value = false;
  }
}

async function toggleRole(role: string) {
  if (!editing.value) return;
  const idx = editing.value.roles.indexOf(role);
  if (idx >= 0) editing.value.roles.splice(idx, 1);
  else editing.value.roles.push(role);
}

async function toggleActive() {
  if (!user.value) return;
  try {
    const newState = !user.value.active;
    await apiPatch(`/api/admin/users/${user.value.id}`, { active: newState });
    user.value.active = newState;
    toast.add({ title: newState ? "已启用账号" : "已禁用账号", color: "success" });
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "操作失败", color: "danger" });
  }
}

function openResetPwd() {
  newPassword.value = "";
  confirmPassword.value = "";
  resetDialog.value = true;
}

async function submitResetPwd() {
  if (!newPassword.value) {
    toast.add({ title: "请输入新密码", color: "warning" });
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    toast.add({ title: "两次密码不一致", color: "warning" });
    return;
  }
  resetting.value = true;
  try {
    await apiPost(`/api/admin/users/${userId.value}/reset-password`, { password: newPassword.value });
    toast.add({ title: "密码重置成功", color: "success" });
    resetDialog.value = false;
  } catch (err: any) {
    toast.add({ title: "重置失败", description: err?.message || "重置失败", color: "danger" });
  } finally {
    resetting.value = false;
  }
}

function goBack() {
  router.back();
}

function activityIcon(type: string) {
  const map: Record<string, string> = {
    login: "material-symbols:login-rounded",
    post_publish: "material-symbols:post-add-rounded",
    post_edit: "material-symbols:edit-document-rounded",
    comment: "material-symbols:chat-bubble-rounded",
    dynamic: "material-symbols:dynamic-form-rounded",
    password_change: "material-symbols:lock-reset-rounded",
    profile_edit: "material-symbols:manage-accounts-rounded",
  };
  return map[type] || "material-symbols:bolt-rounded";
}

function activityColor(type: string) {
  const map: Record<string, string> = {
    login: "text-info-500 bg-info-500/10",
    post_publish: "text-success-500 bg-success-500/10",
    post_edit: "text-primary-500 bg-primary-500/10",
    comment: "text-warning-500 bg-warning-500/10",
    dynamic: "text-nebula-blue bg-primary-500/10",
    password_change: "text-danger-500 bg-danger-500/10",
    profile_edit: "text-info-500 bg-info-500/10",
  };
  return map[type] || "text-neutral-text-tertiary bg-neutral-fill-hover";
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center gap-sm">
      <UButton variant="ghost" size="sm" @click="goBack">
        <UIcon name="material-symbols:arrow-back-rounded" class="w-4 h-4" />
        返回
      </UButton>
      <h1 class="text-2xl font-bold text-neutral-text-primary">用户详情</h1>
    </header>

    <div v-if="pending" class="text-center py-xl text-neutral-text-tertiary">
      <UIcon name="eos-icons:loading" class="w-10 h-10 mx-auto mb-sm animate-spin" />
      <p>加载用户信息中...</p>
    </div>

    <div v-else-if="user" class="grid grid-cols-1 lg:grid-cols-3 gap-md">
      <section class="lg:col-span-1 space-y-md">
        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm overflow-hidden">
          <div class="h-24 bg-gradient-to-r from-primary-500 via-nebula-blue to-info-500" />
          <div class="px-md pb-md">
            <div class="flex items-end justify-between -mt-10 mb-sm">
              <div class="w-20 h-20 rounded-2xl bg-neutral-bg-container border-4 border-neutral-bg-container overflow-hidden shadow-md">
                <img v-if="user.avatar" :src="user.avatar" :alt="user.nickname || user.username" class="w-full h-full object-cover" />
                <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary-500 to-nebula-blue text-white font-bold text-2xl">
                  {{ (user.nickname || user.username || '?').slice(0, 1).toUpperCase() }}
                </div>
              </div>
              <button @click="toggleActive" class="cursor-pointer">
                <UBadge :color="user.active ? 'success' : 'danger'" variant="soft" size="lg">
                  <UIcon :name="user.active ? 'material-symbols:check-circle-rounded' : 'material-symbols:block-rounded'" class="w-3.5 h-3.5 mr-0.5" />
                  {{ user.active ? '已启用' : '已禁用' }}
                </UBadge>
              </button>
            </div>

            <h2 class="text-xl font-bold text-neutral-text-primary">
              {{ user.nickname || user.username }}
              <span class="text-sm font-normal text-neutral-text-tertiary font-mono ml-xs">@{{ user.username }}</span>
            </h2>
            <p v-if="user.bio" class="text-sm text-neutral-text-secondary mt-xs line-clamp-3">{{ user.bio }}</p>

            <div class="mt-md flex flex-wrap gap-xs">
              <UBadge
                v-for="r in (Array.isArray(user.roles) ? user.roles : [])"
                :key="r"
                :color="getRoleMeta(r).color as any"
                variant="subtle"
              >
                {{ getRoleMeta(r).label }}
              </UBadge>
            </div>

            <div class="mt-md grid grid-cols-3 gap-xs border-t border-neutral-border-secondary pt-md">
              <div class="text-center">
                <p class="text-xl font-bold tabular-nums text-neutral-text-primary">{{ user.postsCount || 0 }}</p>
                <p class="text-[10px] text-neutral-text-tertiary uppercase tracking-wider">文章</p>
              </div>
              <div class="text-center border-x border-neutral-border-secondary">
                <p class="text-xl font-bold tabular-nums text-neutral-text-primary">{{ user.commentsCount || 0 }}</p>
                <p class="text-[10px] text-neutral-text-tertiary uppercase tracking-wider">评论</p>
              </div>
              <div class="text-center">
                <p class="text-xl font-bold tabular-nums text-neutral-text-primary">{{ user.dynamicsCount || 0 }}</p>
                <p class="text-[10px] text-neutral-text-tertiary uppercase tracking-wider">动态</p>
              </div>
            </div>

            <div class="mt-md space-y-xs">
              <UButton block variant="ghost" @click="openEdit">
                <UIcon name="material-symbols:edit-rounded" class="w-4 h-4 mr-1" />
                编辑资料
              </UButton>
              <UButton block color="warning" variant="ghost" @click="openResetPwd">
                <UIcon name="material-symbols:lock-reset-rounded" class="w-4 h-4 mr-1" />
                重置密码
              </UButton>
              <UButton
                block
                :color="user.active ? 'danger' : 'success'"
                variant="ghost"
                @click="toggleActive"
              >
                <UIcon :name="user.active ? 'material-symbols:block-rounded' : 'material-symbols:check-circle-rounded'" class="w-4 h-4 mr-1" />
                {{ user.active ? '禁用账号' : '启用账号' }}
              </UButton>
            </div>
          </div>
        </div>

        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <h3 class="font-semibold text-neutral-text-primary mb-sm flex items-center gap-xs">
            <UIcon name="material-symbols:schedule-rounded" class="w-5 h-5 text-primary-500" />
            最近登录
          </h3>
          <div class="space-y-xs text-sm">
            <div class="flex items-center justify-between py-xs border-b border-neutral-border-secondary last:border-0">
              <span class="text-neutral-text-tertiary flex items-center gap-1">
                <UIcon name="material-symbols:login-rounded" class="w-4 h-4" />
                上次登录
              </span>
              <span class="tabular-nums text-neutral-text-secondary text-xs">
                {{ user.lastLoginAt ? dayjs(user.lastLoginAt).format('YYYY-MM-DD HH:mm:ss') : '—' }}
              </span>
            </div>
            <div class="flex items-center justify-between py-xs border-b border-neutral-border-secondary last:border-0">
              <span class="text-neutral-text-tertiary flex items-center gap-1">
                <UIcon name="material-symbols:language-rounded" class="w-4 h-4" />
                登录 IP
              </span>
              <span class="tabular-nums text-neutral-text-secondary text-xs font-mono">{{ user.lastLoginIp || '—' }}</span>
            </div>
            <div class="flex items-center justify-between py-xs border-b border-neutral-border-secondary last:border-0">
              <span class="text-neutral-text-tertiary flex items-center gap-1">
                <UIcon name="material-symbols:counter-1-rounded" class="w-4 h-4" />
                累计登录
              </span>
              <span class="tabular-nums text-neutral-text-secondary text-xs">{{ user.loginCount || 0 }} 次</span>
            </div>
            <div class="flex items-center justify-between py-xs border-b border-neutral-border-secondary last:border-0">
              <span class="text-neutral-text-tertiary flex items-center gap-1">
                <UIcon name="material-symbols:person-add-rounded" class="w-4 h-4" />
                注册时间
              </span>
              <span class="tabular-nums text-neutral-text-secondary text-xs">
                {{ user.createdAt ? dayjs(user.createdAt).format('YYYY-MM-DD HH:mm') : '—' }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="lg:col-span-2 space-y-md">
        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <h3 class="font-semibold text-neutral-text-primary mb-sm flex items-center gap-xs">
            <UIcon name="material-symbols:perm-contact-calendar-rounded" class="w-5 h-5 text-info-500" />
            基础资料
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-md">
            <div>
              <p class="text-xs text-neutral-text-tertiary uppercase tracking-wider mb-0.5">用户名</p>
              <p class="text-neutral-text-primary font-mono">{{ user.username || '—' }}</p>
            </div>
            <div>
              <p class="text-xs text-neutral-text-tertiary uppercase tracking-wider mb-0.5">昵称 / 显示名</p>
              <p class="text-neutral-text-primary">{{ user.nickname || '—' }}</p>
            </div>
            <div>
              <p class="text-xs text-neutral-text-tertiary uppercase tracking-wider mb-0.5">邮箱</p>
              <p class="text-neutral-text-primary">
                <a v-if="user.email" :href="`mailto:${user.email}`" class="hover:text-primary-500 underline-offset-2 hover:underline decoration-dotted">{{ user.email }}</a>
                <span v-else>—</span>
              </p>
            </div>
            <div>
              <p class="text-xs text-neutral-text-tertiary uppercase tracking-wider mb-0.5">所在地</p>
              <p class="text-neutral-text-primary inline-flex items-center gap-0.5">
                <UIcon v-if="user.location" name="material-symbols:location-on-rounded" class="w-4 h-4 text-neutral-text-tertiary" />
                {{ user.location || '—' }}
              </p>
            </div>
            <div>
              <p class="text-xs text-neutral-text-tertiary uppercase tracking-wider mb-0.5">个人网站</p>
              <p class="text-neutral-text-primary">
                <a v-if="user.website" :href="user.website" target="_blank" rel="noopener" class="text-primary-500 hover:text-primary-400 underline-offset-2 hover:underline decoration-dotted truncate block max-w-[280px]">{{ user.website }}</a>
                <span v-else>—</span>
              </p>
            </div>
            <div>
              <p class="text-xs text-neutral-text-tertiary uppercase tracking-wider mb-0.5">GitHub</p>
              <p class="text-neutral-text-primary">
                <a v-if="user.github" :href="`https://github.com/${user.github}`" target="_blank" rel="noopener" class="inline-flex items-center gap-1 hover:text-primary-500">
                  <UIcon name="simple-icons:github" class="w-4 h-4" />{{ user.github }}
                </a>
                <span v-else>—</span>
              </p>
            </div>
            <div class="sm:col-span-2">
              <p class="text-xs text-neutral-text-tertiary uppercase tracking-wider mb-0.5">个人简介</p>
              <p class="text-neutral-text-secondary whitespace-pre-wrap">{{ user.bio || '这个用户很懒，什么也没留下。' }}</p>
            </div>
          </div>
        </div>

        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <h3 class="font-semibold text-neutral-text-primary mb-sm flex items-center gap-xs">
            <UIcon name="material-symbols:shield-person-rounded" class="w-5 h-5 text-danger-500" />
            角色切换
          </h3>
          <p class="text-xs text-neutral-text-tertiary mb-sm">当前已分配角色，点击下方「编辑资料」可调整角色组合。</p>
          <div class="flex flex-wrap gap-sm">
            <div
              v-for="opt in roleOptions"
              :key="opt.value"
              class="flex items-center gap-xs px-sm py-xs rounded-lg border transition-colors"
              :class="(Array.isArray(user.roles) ? user.roles : []).includes(opt.value)
                ? `border-${opt.color}-500/40 bg-${opt.color}-500/5`
                : 'border-neutral-border-secondary bg-neutral-bg-layout opacity-60'"
            >
              <div
                class="w-4 h-4 rounded flex items-center justify-center flex-shrink-0"
                :class="(Array.isArray(user.roles) ? user.roles : []).includes(opt.value) ? `bg-${opt.color}-500` : 'bg-neutral-fill-hover'"
              >
                <UIcon v-if="(Array.isArray(user.roles) ? user.roles : []).includes(opt.value)" name="material-symbols:check-rounded" class="w-3 h-3 text-white" />
              </div>
              <span
                class="text-sm"
                :class="(Array.isArray(user.roles) ? user.roles : []).includes(opt.value) ? `text-${opt.color}-500 font-medium` : 'text-neutral-text-tertiary'"
              >{{ opt.label }}</span>
            </div>
          </div>
        </div>

        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <div class="flex items-center justify-between mb-sm">
            <h3 class="font-semibold text-neutral-text-primary flex items-center gap-xs">
              <UIcon name="material-symbols:timeline-rounded" class="w-5 h-5 text-primary-500" />
              活动时间线
            </h3>
            <span class="text-xs text-neutral-text-tertiary">最近 {{ (user.activities || []).length || 0 }} 条</span>
          </div>
          <div v-if="user.activities && user.activities.length" class="relative pl-sm">
            <div class="absolute left-[15px] top-1 bottom-1 w-px bg-neutral-border-secondary" />
            <div v-for="(act, i) in (user.activities || [])" :key="i" class="relative mb-md last:mb-0">
              <div
                class="absolute -left-0.5 top-0 w-8 h-8 rounded-lg flex items-center justify-center border-4 border-neutral-bg-container z-10"
                :class="activityColor(act.type)"
              >
                <UIcon :name="activityIcon(act.type)" class="w-4 h-4" />
              </div>
              <div class="ml-sm bg-neutral-bg-layout border border-neutral-border-secondary rounded-xl p-sm">
                <div class="flex items-center justify-between mb-xs">
                  <p class="font-medium text-neutral-text-primary text-sm">{{ act.title || act.type }}</p>
                  <span class="text-[10px] text-neutral-text-tertiary tabular-nums flex-shrink-0 ml-xs">
                    {{ act.createdAt ? dayjs(act.createdAt).fromNow() : '' }}
                  </span>
                </div>
                <p v-if="act.description" class="text-xs text-neutral-text-secondary">{{ act.description }}</p>
                <p v-if="act.ip" class="text-[10px] text-neutral-text-quaternary mt-xs font-mono tabular-nums">IP: {{ act.ip }}</p>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-xl text-neutral-text-tertiary text-sm">
            <UIcon name="material-symbols:activity-rounded" class="w-10 h-10 mx-auto mb-xs text-neutral-text-quaternary" />
            <p>暂无活动记录</p>
          </div>
        </div>
      </section>
    </div>

    <UDialog v-model="editOpen" title="编辑用户资料" size="xl">
      <div v-if="editing" class="space-y-sm">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="昵称">
              <UInput v-model="editing.nickname" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="邮箱">
              <UInput v-model="editing.email" type="email" />
            </UFormGroup>
          </div>
        </div>
        <UFormGroup label="个人简介">
          <textarea
            v-model="editing.bio"
            rows="3"
            class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"
          />
        </UFormGroup>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="所在地">
              <UInput v-model="editing.location" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="个人网站">
              <UInput v-model="editing.website" placeholder="https://" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="GitHub 用户名">
              <UInput v-model="editing.github" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="Twitter">
              <UInput v-model="editing.twitter" />
            </UFormGroup>
          </div>
        </div>
        <UFormGroup label="角色分配">
          <div class="flex flex-wrap gap-xs">
            <button
              v-for="opt in roleOptions"
              :key="opt.value"
              type="button"
              @click="toggleRole(opt.value)"
              class="px-3 py-1.5 rounded-lg border text-sm transition-all"
              :class="(editing.roles || []).includes(opt.value)
                ? `border-${opt.color}-500 bg-${opt.color}-500/10 text-${opt.color}-500 font-medium`
                : 'border-neutral-border-secondary bg-neutral-bg-layout text-neutral-text-secondary hover:border-neutral-border-primary'"
            >
              <UIcon
                v-if="(editing.roles || []).includes(opt.value)"
                name="material-symbols:check-rounded"
                class="w-3.5 h-3.5 mr-0.5 inline"
              />
              {{ opt.label }}
            </button>
          </div>
        </UFormGroup>
        <UCheckbox v-model="editing.active" label="账号状态：启用（取消勾选则禁用账号）" />
      </div>
      <template #footer>
        <UButton variant="ghost" @click="editOpen = false">取消</UButton>
        <UButton color="primary" :loading="saving" @click="saveEdit">保存</UButton>
      </template>
    </UDialog>

    <UDialog v-model="resetDialog" title="重置用户密码">
      <div class="space-y-sm">
        <p class="text-sm text-neutral-text-secondary">
          将为用户 <strong class="text-neutral-text-primary">{{ user?.nickname || user?.username }}</strong> 设置新密码。
        </p>
        <UFormGroup label="新密码" required>
          <UInput v-model="newPassword" type="password" placeholder="至少 8 位，建议包含大小写和数字" show-password-toggle />
        </UFormGroup>
        <UFormGroup label="再次确认" required>
          <UInput v-model="confirmPassword" type="password" placeholder="再次输入新密码" show-password-toggle />
        </UFormGroup>
        <UCard variant="outline" class="p-xs text-xs text-warning-500 bg-warning-500/5">
          <UIcon name="material-symbols:warning-rounded" class="w-4 h-4 mr-1 inline" />
          重置密码后，建议通知用户本人及时修改。
        </UCard>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="resetDialog = false">取消</UButton>
        <UButton color="primary" :loading="resetting" @click="submitResetPwd">确认重置</UButton>
      </template>
    </UDialog>
  </div>
</template>

<style scoped>
</style>
