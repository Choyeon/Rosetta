<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "用户管理 - Rosetta 后台" });
const { data, refresh } = await useFetch<any[]>("/api/admin/users", {
  default: () => [], lazy: true, server: false,
});
const editing = ref<any>(null);
function openNew() { editing.value = { id: 0, username: "", email: "", password: "", nickname: "", roles: ["viewer"], active: true }; }
async function save() {
  try {
    const e = editing.value;
    if (e.id) await apiPut(`/api/admin/users/${e.id}`, e);
    else await apiPost("/api/admin/users", e);
    editing.value = null; await refresh();
  } catch (e: any) { alert(e?.message || "保存失败"); }
}
async function toggle(u: any) {
  try { u.active = !u.active; await apiPut(`/api/admin/users/${u.id}`, { active: u.active }); }
  catch (e: any) { u.active = !u.active; alert(e.message); }
}
async function remove(u: any) {
  if (!confirm(`删除用户 ${u.username}?`)) return;
  try { await apiDelete(`/api/admin/users/${u.id}`); await refresh(); }
  catch (e: any) { alert(e.message); }
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-neutral-text-primary">用户管理</h1>
      <button @click="openNew" class="px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 inline-flex items-center gap-1 shadow-sm">
        <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新建用户
      </button>
    </header>

    <section v-if="editing" class="bg-neutral-bg-container border border-primary-500/40 rounded-2xl p-lg shadow-lg ring-4 ring-primary-500/10 max-w-2xl">
      <h3 class="font-semibold mb-sm text-neutral-text-primary">{{ editing.id ? '编辑用户' : '新建用户' }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm text-sm">
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">用户名 *</span>
          <input v-model="editing.username" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">昵称</span>
          <input v-model="editing.nickname" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">邮箱</span>
          <input v-model="editing.email" type="email" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label v-if="!editing.id"><span class="text-xs text-neutral-text-tertiary mb-1 block">初始密码 *</span>
          <input v-model="editing.password" type="password" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">角色 (, 分隔：super_admin / admin / editor / viewer)</span>
          <input v-model="editing.roles" :list="'role-list'" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/>
          <datalist id="role-list"><option value="super_admin"/><option value="admin"/><option value="editor"/><option value="viewer"/></datalist>
        </label>
        <label class="inline-flex items-center gap-xs cursor-pointer select-none"><input v-model="editing.active" type="checkbox" class="w-4 h-4 text-primary-500"/>启用账号</label>
      </div>
      <div class="mt-md flex justify-end gap-xs">
        <button @click="editing = null" class="px-4 h-9 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm">取消</button>
        <button @click="save" class="px-4 h-9 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400">保存</button>
      </div>
    </section>

    <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-neutral-fill-hover text-xs text-neutral-text-tertiary uppercase">
          <tr>
            <th class="px-4 py-3 text-left font-medium">ID</th>
            <th class="px-4 py-3 text-left font-medium">用户</th>
            <th class="px-4 py-3 text-left font-medium hidden md:table-cell">邮箱</th>
            <th class="px-4 py-3 text-left font-medium">角色</th>
            <th class="px-4 py-3 text-left font-medium">状态</th>
            <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">注册 / 登录</th>
            <th class="px-4 py-3 text-right font-medium w-32">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-border-secondary">
          <tr v-for="u in (data || [])" :key="u.id" class="hover:bg-neutral-fill-hover/40">
            <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary">{{ u.id }}</td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-sm">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-nebula-blue text-white flex items-center justify-center font-semibold text-sm">
                  {{ (u.nickname || u.username || '?').slice(0,1) }}
                </div>
                <div>
                  <p class="font-medium text-neutral-text-primary">{{ u.nickname || u.username }}</p>
                  <p class="text-xs text-neutral-text-quaternary">@{{ u.username }}</p>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 hidden md:table-cell text-xs text-neutral-text-secondary">{{ u.email || '—' }}</td>
            <td class="px-4 py-3">
              <span v-for="r in (Array.isArray(u.roles) ? u.roles : [])" :key="r"
                class="mr-xs text-[10px] px-2 py-0.5 rounded font-medium"
                :class="{
                  'bg-danger-500/10 text-danger-500': r === 'super_admin',
                  'bg-primary-500/10 text-primary-500': r === 'admin',
                  'bg-info-500/10 text-info-500': r === 'editor',
                  'bg-neutral-fill-hover text-neutral-text-tertiary': r === 'viewer',
                }">{{ r }}</span>
            </td>
            <td class="px-4 py-3">
              <button @click="toggle(u)"
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                :class="u.active !== false ? 'bg-primary-500' : 'bg-neutral-fill-hover'">
                <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform" :class="u.active !== false ? 'translate-x-6' : 'translate-x-1'"/>
              </button>
            </td>
            <td class="px-4 py-3 text-xs text-neutral-text-tertiary tabular-nums hidden lg:table-cell">
              <p>{{ u.createdAt ? new Date(u.createdAt).toLocaleDateString() : '—' }}</p>
              <p v-if="u.lastLogin" class="mt-0.5 text-neutral-text-quaternary">上次：{{ new Date(u.lastLogin).toLocaleString() }}</p>
            </td>
            <td class="px-4 py-3 text-right text-xs whitespace-nowrap">
              <button @click="editing = structuredClone(u)" class="text-primary-500 hover:text-primary-400 mr-xs inline-flex items-center gap-0.5">
                <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5"/>编辑
              </button>
              <button @click="remove(u)" class="text-danger-500 hover:text-danger-400 inline-flex items-center gap-0.5">
                <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
              </button>
            </td>
          </tr>
          <tr v-if="data?.length === 0"><td colspan="7" class="px-4 py-12 text-center text-sm text-neutral-text-tertiary">暂无用户</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
