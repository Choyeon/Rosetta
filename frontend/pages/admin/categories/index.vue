<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "分类管理 - Rosetta 后台" });
const { data, pending, refresh } = await useFetch<any[]>("/api/admin/categories", {
  default: () => [
    { id: 1, name: "前端开发", slug: "frontend", description: "Nuxt/Vue/React/Astro 等", count: 0 },
    { id: 2, name: "后端开发", slug: "backend", description: "FastAPI/Go/Node", count: 0 },
    { id: 3, name: "项目实战", slug: "projects", description: "", count: 0 },
    { id: 4, name: "迁移笔记", slug: "migration", description: "", count: 0 },
  ],
  lazy: true, server: false,
});
const editing = ref<any>(null);
function openNew() { editing.value = { id: 0, name: "", slug: "", description: "", sort: 0 }; }
async function save() {
  try {
    const e = editing.value;
    if (e.id) await apiPut(`/api/admin/categories/${e.id}`, e);
    else await apiPost("/api/admin/categories", e);
    editing.value = null;
    await refresh();
  } catch (e: any) { alert(e?.message || "保存失败"); }
}
async function remove(id: any) {
  if (!confirm("确定删除该分类？")) return;
  try { await apiDelete(`/api/admin/categories/${id}`); await refresh(); }
  catch (e: any) { alert(e?.message || "删除失败"); }
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-neutral-text-primary">分类管理</h1>
      <button @click="openNew" class="px-4 h-10 inline-flex items-center gap-1 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 shadow-sm">
        <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新建分类
      </button>
    </header>

    <!-- Modal edit -->
    <section v-if="editing" class="bg-neutral-bg-container border border-primary-500/40 rounded-2xl p-lg shadow-lg ring-4 ring-primary-500/10">
      <h3 class="font-semibold text-neutral-text-primary mb-sm">{{ editing.id ? '编辑分类' : '新建分类' }}</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-sm text-sm">
        <label class="block"><span class="text-xs text-neutral-text-tertiary mb-1 block">名称 *</span>
          <input v-model="editing.name" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
        <label class="block"><span class="text-xs text-neutral-text-tertiary mb-1 block">Slug</span>
          <input v-model="editing.slug" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
        <label class="block md:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">描述</span>
          <input v-model="editing.description" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
      </div>
      <div class="mt-md flex justify-end gap-xs">
        <button @click="editing = null" class="px-4 h-9 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm">取消</button>
        <button @click="save" class="px-4 h-9 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400">保存</button>
      </div>
    </section>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-md">
      <div v-for="c in (data || [])" :key="c.id" class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-md hover:shadow-sm transition-all">
        <div class="flex items-start justify-between">
          <h3 class="font-semibold text-neutral-text-primary">{{ c.name }}</h3>
          <span class="px-2 py-0.5 rounded-full bg-neutral-fill-hover text-xs text-neutral-text-tertiary">{{ c.count || 0 }} 篇</span>
        </div>
        <p class="mt-xs text-xs text-neutral-text-quaternary font-mono">slug: {{ c.slug }}</p>
        <p v-if="c.description" class="mt-xs text-sm text-neutral-text-secondary line-clamp-2">{{ c.description }}</p>
        <div class="mt-md pt-sm border-t border-neutral-border-secondary flex items-center justify-between text-xs">
          <button @click="editing = structuredClone(c)" class="text-primary-500 hover:text-primary-400 inline-flex items-center gap-0.5">
            <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5"/>编辑
          </button>
          <button @click="remove(c.id)" class="text-danger-500 hover:text-danger-400 inline-flex items-center gap-0.5">
            <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
