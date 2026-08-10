<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "菜单管理 - Rosetta 后台" });
const { data, refresh } = await useFetch<any[]>("/api/admin/menus", {
  default: () => [
    { id: 1, name: "首页", type: "route", target: "/", sort: 0, enabled: true },
    { id: 2, name: "文章", type: "route", target: "/posts", sort: 1, enabled: true },
    { id: 3, name: "归档", type: "route", target: "/archive", sort: 2, enabled: true },
    { id: 4, name: "友链", type: "route", target: "/friends", sort: 3, enabled: true },
    { id: 5, name: "关于", type: "route", target: "/about", sort: 4, enabled: true },
  ], lazy: true, server: false,
});
const editing = ref<any>(null);
function openNew(pid = 0) { editing.value = { id: 0, name: "", type: "route", target: "/", parentId: pid, sort: 0, enabled: true }; }
async function save() {
  try {
    const e = editing.value;
    if (e.id) await apiPut(`/api/admin/menus/${e.id}`, e);
    else await apiPost("/api/admin/menus", e);
    editing.value = null; await refresh();
  } catch (e: any) { alert(e?.message || "保存失败"); }
}
async function remove(id: any) {
  if (!confirm("删除该菜单项？")) return;
  try { await apiDelete(`/api/admin/menus/${id}`); await refresh(); }
  catch (e: any) { alert(e.message); }
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-neutral-text-primary">菜单管理</h1>
      <button @click="openNew()" class="px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 inline-flex items-center gap-1 shadow-sm">
        <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新增菜单
      </button>
    </header>

    <section v-if="editing" class="bg-neutral-bg-container border border-primary-500/40 rounded-2xl p-lg shadow-lg ring-4 ring-primary-500/10 max-w-2xl">
      <h3 class="font-semibold mb-sm text-neutral-text-primary">{{ editing.id ? '编辑菜单' : '新增菜单' }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm text-sm">
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">名称</span>
          <input v-model="editing.name" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">类型</span>
          <select v-model="editing.type" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
            <option value="route">站内路由</option>
            <option value="link">外部链接</option>
            <option value="category">分类页</option>
            <option value="page">独立页</option>
          </select>
        </label>
        <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">目标（路径 / URL / slug）</span>
          <input v-model="editing.target" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">父级</span>
          <input v-model.number="editing.parentId" type="number" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">排序</span>
          <input v-model.number="editing.sort" type="number" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label class="inline-flex items-center gap-xs cursor-pointer select-none"><input v-model="editing.enabled" type="checkbox" class="w-4 h-4 text-primary-500"/>启用</label>
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
            <th class="px-4 py-3 text-left font-medium w-16">ID</th>
            <th class="px-4 py-3 text-left font-medium">名称</th>
            <th class="px-4 py-3 text-left font-medium hidden md:table-cell">类型 · 目标</th>
            <th class="px-4 py-3 text-left font-medium">父级</th>
            <th class="px-4 py-3 text-left font-medium">排序</th>
            <th class="px-4 py-3 text-left font-medium">状态</th>
            <th class="px-4 py-3 text-right font-medium w-40">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-border-secondary">
          <tr v-for="m in ((data||[]).sort((a,b)=>a.sort-b.sort))" :key="m.id" class="hover:bg-neutral-fill-hover/40">
            <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary">{{ m.id }}</td>
            <td class="px-4 py-3 font-medium text-neutral-text-primary">{{ m.name }}</td>
            <td class="px-4 py-3 hidden md:table-cell">
              <span class="text-xs px-2 py-0.5 rounded bg-neutral-fill-hover text-neutral-text-secondary mr-xs">{{ m.type }}</span>
              <code class="text-xs text-neutral-text-tertiary truncate">{{ m.target }}</code>
            </td>
            <td class="px-4 py-3 text-xs text-neutral-text-secondary">{{ m.parentId || '—' }}</td>
            <td class="px-4 py-3 font-mono text-xs tabular-nums">{{ m.sort }}</td>
            <td class="px-4 py-3">
              <span v-if="m.enabled" class="text-[10px] px-2 py-0.5 rounded bg-success-500/10 text-success-600 font-semibold">启用</span>
              <span v-else class="text-[10px] px-2 py-0.5 rounded bg-neutral-fill-hover text-neutral-text-tertiary">停用</span>
            </td>
            <td class="px-4 py-3 text-right text-xs whitespace-nowrap">
              <button @click="openNew(m.id)" class="text-info-500 hover:text-info-400 mr-xs inline-flex items-center gap-0.5">
                <Icon name="material-symbols:subdirectory-arrow-right-rounded" class="w-3.5 h-3.5"/>子菜单
              </button>
              <button @click="editing = structuredClone(m)" class="text-primary-500 hover:text-primary-400 mr-xs inline-flex items-center gap-0.5">
                <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5"/>编辑
              </button>
              <button @click="remove(m.id)" class="text-danger-500 hover:text-danger-400 inline-flex items-center gap-0.5">
                <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
