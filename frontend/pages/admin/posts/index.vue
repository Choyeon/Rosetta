<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "文章管理 - Rosetta 后台" });
const route = useRoute();
const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const status = ref<String>(String(route.query.status || "all"));
const category = ref(String(route.query.category || ""));
watch([() => route.query.page, () => route.query.q, () => route.query.status, () => route.query.category], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  status.value = String(route.query.status || "all");
  category.value = String(route.query.category || "");
});

const { data, pending, refresh } = await useFetch<any>(() => "/api/admin/posts", {
  query: computed(() => ({ page: page.value, pageSize, keyword: keyword.value, status: status.value !== "all" ? status.value : undefined, category: category.value || undefined })),
  default: () => ({ items: [], total: 0, totalPages: 1 }),
  lazy: true,
  server: false,
});

const deleting = ref<number | string | null>(null);
async function remove(id: number | string) {
  if (!confirm("确定删除该文章？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/posts/${id}`);
    await refresh();
  } catch (e: any) {
    alert(e?.message || "删除失败");
  } finally { deleting.value = null; }
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-sm">
      <h1 class="text-2xl font-bold text-neutral-text-primary">文章管理</h1>
      <NuxtLink to="/admin/posts/new" class="px-4 h-10 inline-flex items-center gap-1.5 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 shadow-sm">
        <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新建文章
      </NuxtLink>
    </header>

    <!-- Filters -->
    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs"
      @submit.prevent="navigateTo({ path: '/admin/posts', query: { q: keyword || undefined, status: status !== 'all' ? status : undefined, category: category || undefined, page: 1 } })"
    >
      <input v-model="keyword" type="search" placeholder="搜索标题 / slug / 描述"
        class="sm:flex-1 h-10 px-4 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/>
      <select v-model="status" class="h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40">
        <option value="all">全部状态</option>
        <option value="published">已发布</option>
        <option value="draft">草稿</option>
        <option value="hidden">隐藏</option>
      </select>
      <input v-model="category" placeholder="分类筛选" class="h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40 sm:w-40"/>
      <button type="submit" class="h-10 px-5 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm font-medium inline-flex items-center gap-1">
        <Icon name="material-symbols:filter-list-rounded" class="w-4 h-4"/>筛选
      </button>
    </form>

    <!-- Table -->
    <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-neutral-fill-hover text-xs text-neutral-text-tertiary uppercase tracking-wider">
            <tr>
              <th class="px-4 py-3 text-left font-medium w-16">ID</th>
              <th class="px-4 py-3 text-left font-medium">标题</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">分类 / 标签</th>
              <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">作者</th>
              <th class="px-4 py-3 text-left font-medium">状态</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">发布</th>
              <th class="px-4 py-3 text-right font-medium w-32">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="p in (data?.items || [])" :key="p.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums">{{ p.id }}</td>
              <td class="px-4 py-3 font-medium text-neutral-text-primary min-w-[200px]">
                <NuxtLink :to="`/posts/${p.slug||p.id}`" target="_blank" class="hover:text-primary-500 underline-offset-2 hover:underline decoration-dotted">{{ p.title }}</NuxtLink>
              </td>
              <td class="px-4 py-3 hidden md:table-cell">
                <span v-if="p.category" class="text-xs px-2 py-0.5 rounded bg-primary-500/10 text-primary-500 font-medium mr-xs">{{ p.category }}</span>
                <span v-for="t in (p.tags||[]).slice(0,3)" :key="t" class="text-xs text-neutral-text-tertiary mr-xs">#{{ t }}</span>
              </td>
              <td class="px-4 py-3 hidden lg:table-cell text-xs text-neutral-text-secondary">{{ p.author || '—' }}</td>
              <td class="px-4 py-3">
                <span v-if="p.status === 'published' || p.published" class="px-2 py-0.5 rounded text-[10px] font-semibold bg-success-500/10 text-success-600">已发布</span>
                <span v-else-if="p.status === 'hidden'" class="px-2 py-0.5 rounded text-[10px] font-semibold bg-warning-500/10 text-warning-600">隐藏</span>
                <span v-else class="px-2 py-0.5 rounded text-[10px] font-semibold bg-neutral-fill-hover text-neutral-text-tertiary">草稿</span>
                <span v-if="p.pinned" class="ml-xs text-[10px] px-1.5 py-0.5 rounded bg-warning-500/10 text-warning-600">PIN</span>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell tabular-nums">
                {{ p.published ? new Date(p.published).toLocaleString() : (p.updatedAt ? new Date(p.updatedAt).toLocaleString() : '—') }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <NuxtLink :to="`/admin/posts/${p.id}`" class="text-primary-500 hover:text-primary-400 text-xs font-medium mr-xs inline-flex items-center gap-0.5">
                  <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5"/>编辑
                </NuxtLink>
                <button
                  :disabled="deleting === p.id"
                  @click="remove(p.id)"
                  class="text-danger-500 hover:text-danger-400 text-xs font-medium inline-flex items-center gap-0.5 disabled:opacity-50"
                >
                  <Icon v-if="deleting === p.id" name="eos-icons:loading" class="w-3.5 h-3.5 animate-spin"/>
                  <Icon v-else name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
                </button>
              </td>
            </tr>
            <tr v-if="!pending && data?.items?.length === 0">
              <td colspan="7" class="px-4 py-12 text-center text-neutral-text-tertiary text-sm">没有文章</td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- Pagination -->
      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/posts', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else/>
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }}</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/posts', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>
  </div>
</template>
