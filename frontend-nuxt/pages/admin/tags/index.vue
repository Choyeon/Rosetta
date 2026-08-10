<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "标签管理 - Rosetta 后台" });
const { data, pending, refresh } = await useFetch<any[]>("/api/admin/tags", {
  default: () => [
    { id: 1, name: "Nuxt", slug: "nuxt", count: 0 },
    { id: 2, name: "Vue", slug: "vue", count: 0 },
    { id: 3, name: "FastAPI", slug: "fastapi", count: 0 },
    { id: 4, name: "迁移", slug: "migration", count: 0 },
  ],
  lazy: true, server: false,
});
const editing = ref<any>(null);
const batchAdd = ref("");
function openNew() { editing.value = { id: 0, name: "", slug: "" }; }
async function save() {
  try {
    const e = editing.value;
    if (e.id) await apiPut(`/api/admin/tags/${e.id}`, e);
    else await apiPost("/api/admin/tags", e);
    editing.value = null;
    await refresh();
  } catch (e: any) { alert(e?.message || "保存失败"); }
}
async function bulk() {
  const names = batchAdd.value.split(/[,，\n]/).map(s => s.trim()).filter(Boolean);
  if (!names.length) return;
  try { for (const n of names) await apiPost("/api/admin/tags", { name: n }); await refresh(); batchAdd.value = ""; }
  catch (e: any) { alert(e?.message || "批量新增失败"); }
}
async function remove(id: any) {
  if (!confirm("确定删除该标签？")) return;
  try { await apiDelete(`/api/admin/tags/${id}`); await refresh(); }
  catch (e: any) { alert(e?.message || "删除失败"); }
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-neutral-text-primary">标签管理</h1>
      <button @click="openNew" class="px-4 h-10 inline-flex items-center gap-1 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 shadow-sm">
        <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新建标签
      </button>
    </header>

    <!-- 批量新增 -->
    <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-md">
      <p class="text-xs text-neutral-text-tertiary mb-xs">批量新增标签（逗号或换行分隔）</p>
      <div class="flex gap-xs">
        <textarea v-model="batchAdd" rows="2" placeholder="Vue3, Nuxt4, Vite, Tailwind, Pinia..." class="flex-1 p-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"/>
        <button @click="bulk" class="h-10 px-4 self-start rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm">批量添加</button>
      </div>
    </section>

    <section v-if="editing" class="bg-neutral-bg-container border border-primary-500/40 rounded-2xl p-lg shadow-lg ring-4 ring-primary-500/10">
      <h3 class="font-semibold mb-sm text-neutral-text-primary">{{ editing.id ? '编辑标签' : '新建标签' }}</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-sm text-sm">
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">名称 *</span>
          <input v-model="editing.name" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Slug</span>
          <input v-model="editing.slug" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
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
            <th class="px-4 py-3 text-left font-medium">名称</th>
            <th class="px-4 py-3 text-left font-medium">Slug</th>
            <th class="px-4 py-3 text-left font-medium">文章数</th>
            <th class="px-4 py-3 text-right font-medium w-32">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-border-secondary">
          <tr v-for="t in (data || [])" :key="t.id" class="hover:bg-neutral-fill-hover/40">
            <td class="px-4 py-3 font-medium text-neutral-text-primary">#{{ t.name }}</td>
            <td class="px-4 py-3 text-xs font-mono text-neutral-text-tertiary">{{ t.slug }}</td>
            <td class="px-4 py-3 text-xs text-neutral-text-secondary tabular-nums">{{ t.count || 0 }}</td>
            <td class="px-4 py-3 text-right text-xs space-x-xs whitespace-nowrap">
              <button @click="editing = structuredClone(t)" class="text-primary-500 hover:text-primary-400 inline-flex items-center gap-0.5">
                <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5"/>编辑
              </button>
              <button @click="remove(t.id)" class="text-danger-500 hover:text-danger-400 inline-flex items-center gap-0.5">
                <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
