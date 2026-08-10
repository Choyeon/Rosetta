<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "独立页面管理 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const statusFilter = ref<String>(String(route.query.status || "all"));

watch([() => route.query.page, () => route.query.q, () => route.query.status], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  statusFilter.value = String(route.query.status || "all");
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/pages", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    status: statusFilter.value !== "all" ? statusFilter.value : undefined,
  })),
  default: () => ({ items: [], total: 0, totalPages: 1 }),
  lazy: true,
  server: false,
});

const dialogOpen = ref(false);
const editing = ref<any>(null);
const deleting = ref<number | string | null>(null);
const previewOpen = ref(false);
const previewContent = ref("");
const previewTitle = ref("");

const statusMap: Record<string, { label: string; color: string }> = {
  published: { label: "已发布", color: "success" },
  draft: { label: "草稿", color: "warning" },
  hidden: { label: "隐藏", color: "neutral" },
};

function renderMarkdown(md: string) {
  if (!md) return "";
  return md
    .replace(/^### (.*)$/gm, '<h3 class="text-lg font-bold mb-2 mt-4">$1</h3>')
    .replace(/^## (.*)$/gm, '<h2 class="text-xl font-bold mb-2 mt-4">$1</h2>')
    .replace(/^# (.*)$/gm, '<h1 class="text-2xl font-bold mb-3 mt-4">$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-neutral-fill-hover text-xs font-mono text-danger-500">$1</code>')
    .replace(/^- (.*)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/^(\d+)\. (.*)$/gm, '<li class="ml-4 list-decimal">$2</li>')
    .replace(/\n\n/g, '</p><p class="mb-3">')
    .replace(/\n/g, '<br/>');
}
// 将 v-html 表达式搬到 computed 里 — 避免 Vue 模板双引号属性里再写 \" 转义导致 Unterminated string
const previewLiveHtml = computed(() => `<p class="mb-3">${renderMarkdown(editing.value?.content || "")}</p>`);

function openNew() {
  editing.value = {
    id: 0,
    title: "",
    slug: "",
    content: "",
    status: "draft",
    publishedAt: "",
  };
  dialogOpen.value = true;
}

function openEdit(item: any) {
  editing.value = structuredClone(item);
  dialogOpen.value = true;
}

function openPreview(item: any) {
  previewTitle.value = item.title;
  previewContent.value = renderMarkdown(item.content || "");
  previewOpen.value = true;
}

async function save() {
  try {
    const e = editing.value;
    if (e.id) {
      await apiPut(`/api/admin/pages/${e.id}`, e);
      toast.add({ title: "更新成功", color: "success" });
    } else {
      await apiPost("/api/admin/pages", e);
      toast.add({ title: "创建成功", color: "success" });
    }
    dialogOpen.value = false;
    editing.value = null;
    await refresh();
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "保存失败", color: "danger" });
  }
}

async function toggleStatus(item: any, status: string) {
  try {
    await apiPatch(`/api/admin/pages/${item.id}`, { status });
    item.status = status;
    toast.add({ title: "状态已更新", color: "success" });
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "状态切换失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该页面？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/pages/${id}`);
    toast.add({ title: "删除成功", color: "success" });
    await refresh();
  } catch (err: any) {
    toast.add({ title: "删除失败", description: err?.message || "删除失败", color: "danger" });
  } finally {
    deleting.value = null;
  }
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-sm">
      <h1 class="text-2xl font-bold text-neutral-text-primary">独立页面管理</h1>
      <UButton color="primary" @click="openNew">
        <UIcon name="material-symbols:add-rounded" class="w-4 h-4 mr-1" />
        新建页面
      </UButton>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs"
      @submit.prevent="navigateTo({ path: '/admin/pages', query: { q: keyword || undefined, status: statusFilter !== 'all' ? statusFilter : undefined, page: 1 } })"
    >
      <UInput v-model="keyword" type="search" placeholder="搜索标题 / slug / 内容" class="sm:flex-1" />
      <USelect v-model="statusFilter" class="sm:w-40">
        <option value="all">全部状态</option>
        <option v-for="(v, k) in statusMap" :key="k" :value="k">{{ v.label }}</option>
      </USelect>
      <UButton type="submit" variant="ghost">
        <UIcon name="material-symbols:filter-list-rounded" class="w-4 h-4 mr-1" />
        筛选
      </UButton>
    </form>

    <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-neutral-fill-hover text-xs text-neutral-text-tertiary uppercase tracking-wider">
            <tr>
              <th class="px-4 py-3 text-left font-medium w-16">ID</th>
              <th class="px-4 py-3 text-left font-medium">标题 / Slug</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">摘要</th>
              <th class="px-4 py-3 text-left font-medium">状态</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">发布时间</th>
              <th class="px-4 py-3 text-right font-medium w-48">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums">{{ item.id }}</td>
              <td class="px-4 py-3 min-w-[200px]">
                <p class="font-medium text-neutral-text-primary">{{ item.title }}</p>
                <a :href="`/${item.slug || item.id}`" target="_blank" class="text-xs font-mono text-primary-500 hover:text-primary-400 mt-0.5 inline-flex items-center gap-0.5">
                  <UIcon name="material-symbols:open-in-new-rounded" class="w-3 h-3" />
                  /{{ item.slug || item.id }}
                </a>
              </td>
              <td class="px-4 py-3 hidden md:table-cell text-xs text-neutral-text-secondary line-clamp-2 max-w-[300px]">
                {{ (item.content || '').replace(/[#*`\[\]>_\-]/g, '').slice(0, 120) || '—' }}
              </td>
              <td class="px-4 py-3">
                <UBadge :color="statusMap[item.status]?.color || 'neutral'" variant="subtle">
                  {{ statusMap[item.status]?.label || item.status }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell tabular-nums">
                {{ item.publishedAt ? dayjs(item.publishedAt).format('YYYY-MM-DD HH:mm') : '—' }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <UButton size="xs" variant="ghost" color="neutral" class="mr-1" @click="openPreview(item)">
                  <UIcon name="material-symbols:visibility-rounded" class="w-3.5 h-3.5 mr-0.5" />
                  预览
                </UButton>
                <UButton size="xs" variant="ghost" color="primary" class="mr-1" @click="openEdit(item)">
                  <UIcon name="material-symbols:edit-rounded" class="w-3.5 h-3.5 mr-0.5" />
                  编辑
                </UButton>
                <UButton
                  size="xs"
                  variant="ghost"
                  color="danger"
                  :disabled="deleting === item.id"
                  @click="remove(item.id)"
                >
                  <UIcon v-if="deleting === item.id" name="eos-icons:loading" class="w-3.5 h-3.5 animate-spin" />
                  <UIcon v-else name="material-symbols:delete-rounded" class="w-3.5 h-3.5 mr-0.5" />
                  删除
                </UButton>
              </td>
            </tr>
            <tr v-if="!pending && data?.items?.length === 0">
              <td colspan="6" class="px-4 py-12 text-center text-neutral-text-tertiary text-sm">
                <UIcon name="material-symbols:article-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无独立页面</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/pages', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 条</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/pages', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="dialogOpen" :title="editing?.id ? '编辑页面' : '新建页面'" size="3xl">
      <div v-if="editing" class="space-y-sm">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="页面标题" required>
              <UInput v-model="editing.title" placeholder="例如：关于我们" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="Slug（URL 路径）">
              <UInput v-model="editing.slug" placeholder="about" />
            </UFormGroup>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="状态">
              <USelect v-model="editing.status">
                <option v-for="(v, k) in statusMap" :key="k" :value="k">{{ v.label }}</option>
              </USelect>
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="发布时间（留空为立即）">
              <UInput v-model="editing.publishedAt" type="datetime-local" />
            </UFormGroup>
          </div>
        </div>
        <UFormGroup label="页面内容（Markdown）" required>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-xs">
            <textarea
              v-model="editing.content"
              rows="14"
              placeholder="# 标题&#10;&#10;这里是正文，支持 **粗体**、*斜体*、`代码`、列表等 Markdown 语法..."
              class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"
            />
            <div class="rounded-lg border border-neutral-border-secondary bg-neutral-bg-layout p-3 overflow-y-auto max-h-80 prose-sm text-sm">
              <p class="text-xs text-neutral-text-tertiary mb-xs border-b border-neutral-border-secondary pb-xs flex items-center gap-1">
                <UIcon name="material-symbols:preview-rounded" class="w-3.5 h-3.5" />
                实时预览
              </p>
              <div class="text-neutral-text-primary leading-relaxed" v-html="previewLiveHtml" />
            </div>
          </div>
        </UFormGroup>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="dialogOpen = false">取消</UButton>
        <UButton color="primary" @click="save">保存</UButton>
      </template>
    </UDialog>

    <UDialog v-model="previewOpen" :title="previewTitle" size="2xl">
      <div class="prose prose-sm max-w-none text-neutral-text-primary leading-relaxed" v-html="previewContent" />
    </UDialog>
  </div>
</template>

<style scoped>
</style>
