<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "站点公告 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const typeFilter = ref<String>(String(route.query.type || "all"));
const levelFilter = ref<String>(String(route.query.level || "all"));

watch([() => route.query.page, () => route.query.q, () => route.query.type, () => route.query.level], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  typeFilter.value = String(route.query.type || "all");
  levelFilter.value = String(route.query.level || "all");
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/announcements", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    type: typeFilter.value !== "all" ? typeFilter.value : undefined,
    level: levelFilter.value !== "all" ? levelFilter.value : undefined,
  })),
  default: () => ({ items: [], total: 0, totalPages: 1 }),
  lazy: true,
  server: false,
});

const dialogOpen = ref(false);
const editing = ref<any>(null);
const deleting = ref<number | string | null>(null);

const typeOptions = [
  { value: "info", label: "普通通知", color: "info" },
  { value: "warning", label: "警告提示", color: "warning" },
  { value: "danger", label: "紧急公告", color: "danger" },
  { value: "success", label: "成功消息", color: "success" },
];
const levelOptions = [
  { value: "low", label: "低", color: "neutral" },
  { value: "medium", label: "中", color: "info" },
  { value: "high", label: "高", color: "warning" },
  { value: "critical", label: "紧急", color: "danger" },
];

function getTypeMeta(v: string) {
  return typeOptions.find(o => o.value === v) || { label: v, color: "neutral" };
}
function getLevelMeta(v: string) {
  return levelOptions.find(o => o.value === v) || { label: v, color: "neutral" };
}

function openNew() {
  editing.value = {
    id: 0,
    title: "",
    content: "",
    type: "info",
    level: "medium",
    startAt: "",
    endAt: "",
    priority: 0,
    published: true,
  };
  dialogOpen.value = true;
}

function openEdit(item: any) {
  editing.value = structuredClone(item);
  dialogOpen.value = true;
}

async function save() {
  try {
    const e = editing.value;
    if (e.id) {
      await apiPut(`/api/admin/announcements/${e.id}`, e);
      toast.add({ title: "更新成功", description: `公告「${e.title}」已更新`, color: "success" });
    } else {
      await apiPost("/api/admin/announcements", e);
      toast.add({ title: "创建成功", description: `公告「${e.title}」已创建`, color: "success" });
    }
    dialogOpen.value = false;
    editing.value = null;
    await refresh();
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "保存失败", color: "danger" });
  }
}

async function togglePublished(item: any) {
  try {
    const newState = !item.published;
    await apiPatch(`/api/admin/announcements/${item.id}`, { published: newState });
    item.published = newState;
    toast.add({ title: "状态已更新", color: "success" });
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "状态切换失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该公告？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/announcements/${id}`);
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
      <h1 class="text-2xl font-bold text-neutral-text-primary">站点公告</h1>
      <UButton color="primary" @click="openNew">
        <UIcon name="material-symbols:add-rounded" class="w-4 h-4 mr-1" />
        发布公告
      </UButton>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs flex-wrap"
      @submit.prevent="navigateTo({ path: '/admin/announcements', query: { q: keyword || undefined, type: typeFilter !== 'all' ? typeFilter : undefined, level: levelFilter !== 'all' ? levelFilter : undefined, page: 1 } })"
    >
      <UInput v-model="keyword" type="search" placeholder="搜索标题 / 内容" class="sm:flex-1 min-w-[200px]" />
      <USelect v-model="typeFilter" class="sm:w-36">
        <option value="all">全部类型</option>
        <option v-for="o in typeOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
      </USelect>
      <USelect v-model="levelFilter" class="sm:w-36">
        <option value="all">全部级别</option>
        <option v-for="o in levelOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
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
              <th class="px-4 py-3 text-left font-medium">标题</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">类型</th>
              <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">级别</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">优先级</th>
              <th class="px-4 py-3 text-left font-medium">发布状态</th>
              <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">有效时间</th>
              <th class="px-4 py-3 text-right font-medium w-36">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums">{{ item.id }}</td>
              <td class="px-4 py-3 min-w-[200px]">
                <p class="font-medium text-neutral-text-primary">{{ item.title }}</p>
                <p v-if="item.content" class="text-xs text-neutral-text-secondary mt-1 line-clamp-1">{{ item.content }}</p>
              </td>
              <td class="px-4 py-3 hidden md:table-cell">
                <UBadge :color="getTypeMeta(item.type).color" variant="subtle">
                  {{ getTypeMeta(item.type).label }}
                </UBadge>
              </td>
              <td class="px-4 py-3 hidden lg:table-cell">
                <UBadge :color="getLevelMeta(item.level).color" variant="subtle">
                  {{ getLevelMeta(item.level).label }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell tabular-nums">{{ item.priority ?? 0 }}</td>
              <td class="px-4 py-3">
                <button @click="togglePublished(item)" class="cursor-pointer">
                  <UBadge :color="item.published ? 'success' : 'neutral'" variant="subtle">
                    {{ item.published ? '已发布' : '未发布' }}
                  </UBadge>
                </button>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden lg:table-cell tabular-nums">
                <p v-if="item.startAt">起：{{ dayjs(item.startAt).format('MM-DD HH:mm') }}</p>
                <p v-if="item.endAt">止：{{ dayjs(item.endAt).format('MM-DD HH:mm') }}</p>
                <p v-if="!item.startAt && !item.endAt">永久有效</p>
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
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
              <td colspan="8" class="px-4 py-12 text-center text-neutral-text-tertiary text-sm">
                <UIcon name="material-symbols:campaign-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无公告</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/announcements', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 条</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/announcements', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="dialogOpen" :title="editing?.id ? '编辑公告' : '发布公告'" size="2xl">
      <div v-if="editing" class="space-y-sm">
        <UFormGroup label="公告标题" required>
          <UInput v-model="editing.title" placeholder="请输入公告标题" />
        </UFormGroup>
        <UFormGroup label="公告内容" required>
          <textarea
            v-model="editing.content"
            rows="4"
            placeholder="公告详细内容，支持换行..."
            class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"
          />
        </UFormGroup>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="公告类型">
              <USelect v-model="editing.type">
                <option v-for="o in typeOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </USelect>
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="紧急级别">
              <USelect v-model="editing.level">
                <option v-for="o in levelOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </USelect>
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="生效时间（可选）">
              <UInput v-model="editing.startAt" type="datetime-local" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="失效时间（可选）">
              <UInput v-model="editing.endAt" type="datetime-local" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="优先级（越大越靠前）">
              <UInput v-model.number="editing.priority" type="number" />
            </UFormGroup>
          </div>
          <div class="flex items-end">
            <UCheckbox v-model="editing.published" label="立即发布" class="mb-2" />
          </div>
        </div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="dialogOpen = false">取消</UButton>
        <UButton color="primary" @click="save">保存</UButton>
      </template>
    </UDialog>
  </div>
</template>

<style scoped>
</style>
