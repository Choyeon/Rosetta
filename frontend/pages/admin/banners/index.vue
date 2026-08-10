<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "轮播横幅 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const enabledFilter = ref<String>(String(route.query.enabled || "all"));

watch([() => route.query.page, () => route.query.q, () => route.query.enabled], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  enabledFilter.value = String(route.query.enabled || "all");
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/banners", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    enabled: enabledFilter.value !== "all" ? enabledFilter.value : undefined,
  })),
  default: () => ({ items: [], total: 0, totalPages: 1 }),
  lazy: true,
  server: false,
});

const dialogOpen = ref(false);
const editing = ref<any>(null);
const deleting = ref<number | string | null>(null);
const previewOpen = ref(false);
const previewItem = ref<any>(null);

const targetOptions = [
  { value: "_self", label: "当前窗口" },
  { value: "_blank", label: "新窗口" },
];

function openNew() {
  editing.value = {
    id: 0,
    title: "",
    subtitle: "",
    image: "",
    link: "",
    target: "_self",
    sort: 0,
    startAt: "",
    endAt: "",
    enabled: true,
  };
  dialogOpen.value = true;
}

function openEdit(item: any) {
  editing.value = structuredClone(item);
  dialogOpen.value = true;
}

function openPreview(item: any) {
  previewItem.value = item;
  previewOpen.value = true;
}

async function save() {
  try {
    const e = editing.value;
    if (e.id) {
      await apiPut(`/api/admin/banners/${e.id}`, e);
      toast.add({ title: "更新成功", color: "success" });
    } else {
      await apiPost("/api/admin/banners", e);
      toast.add({ title: "创建成功", color: "success" });
    }
    dialogOpen.value = false;
    editing.value = null;
    await refresh();
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "保存失败", color: "danger" });
  }
}

async function toggleEnabled(item: any) {
  try {
    const newState = !item.enabled;
    await apiPatch(`/api/admin/banners/${item.id}`, { enabled: newState });
    item.enabled = newState;
    toast.add({ title: "状态已更新", color: "success" });
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "状态切换失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该横幅？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/banners/${id}`);
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
      <h1 class="text-2xl font-bold text-neutral-text-primary">首屏轮播横幅</h1>
      <UButton color="primary" @click="openNew">
        <UIcon name="material-symbols:add-rounded" class="w-4 h-4 mr-1" />
        新建横幅
      </UButton>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs"
      @submit.prevent="navigateTo({ path: '/admin/banners', query: { q: keyword || undefined, enabled: enabledFilter !== 'all' ? enabledFilter : undefined, page: 1 } })"
    >
      <UInput v-model="keyword" type="search" placeholder="搜索标题 / 副标题" class="sm:flex-1" />
      <USelect v-model="enabledFilter" class="sm:w-40">
        <option value="all">全部状态</option>
        <option value="true">启用中</option>
        <option value="false">已停用</option>
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
              <th class="px-4 py-3 text-left font-medium">预览</th>
              <th class="px-4 py-3 text-left font-medium">标题 / 副标题</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">跳转</th>
              <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">排序</th>
              <th class="px-4 py-3 text-left font-medium">启用</th>
              <th class="px-4 py-3 text-left font-medium hidden xl:table-cell">有效期</th>
              <th class="px-4 py-3 text-right font-medium w-44">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums">{{ item.id }}</td>
              <td class="px-4 py-3">
                <button @click="openPreview(item)" class="w-24 h-14 rounded-lg overflow-hidden bg-neutral-fill-hover block">
                  <img v-if="item.image" :src="item.image" :alt="item.title" class="w-full h-full object-cover" />
                  <div v-else class="w-full h-full flex items-center justify-center">
                    <UIcon name="material-symbols:image-rounded" class="w-6 h-6 text-neutral-text-tertiary" />
                  </div>
                </button>
              </td>
              <td class="px-4 py-3 min-w-[200px]">
                <p class="font-medium text-neutral-text-primary">{{ item.title || '（无标题）' }}</p>
                <p v-if="item.subtitle" class="text-xs text-neutral-text-secondary mt-0.5">{{ item.subtitle }}</p>
              </td>
              <td class="px-4 py-3 hidden md:table-cell text-xs text-neutral-text-secondary max-w-[200px]">
                <a v-if="item.link" :href="item.link" :target="item.target" class="truncate block hover:text-primary-500 underline-offset-2 hover:underline decoration-dotted">
                  {{ item.link }}
                </a>
                <span v-else class="text-neutral-text-quaternary">无链接</span>
                <p class="text-[10px] text-neutral-text-quaternary mt-0.5">
                  {{ targetOptions.find(t => t.value === item.target)?.label || item.target }}
                </p>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden lg:table-cell tabular-nums">{{ item.sort ?? 0 }}</td>
              <td class="px-4 py-3">
                <button @click="toggleEnabled(item)" class="cursor-pointer">
                  <UBadge :color="item.enabled ? 'success' : 'neutral'" variant="subtle">
                    {{ item.enabled ? '启用' : '停用' }}
                  </UBadge>
                </button>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden xl:table-cell tabular-nums">
                <p v-if="item.startAt">起：{{ dayjs(item.startAt).format('MM-DD') }}</p>
                <p v-if="item.endAt">止：{{ dayjs(item.endAt).format('MM-DD') }}</p>
                <p v-if="!item.startAt && !item.endAt">永久</p>
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
              <td colspan="8" class="px-4 py-12 text-center text-neutral-text-tertiary text-sm">
                <UIcon name="material-symbols:panorama-horizontal-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无横幅</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/banners', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 条</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/banners', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="dialogOpen" :title="editing?.id ? '编辑横幅' : '新建横幅'" size="2xl">
      <div v-if="editing" class="space-y-sm">
        <UFormGroup label="主标题">
          <UInput v-model="editing.title" placeholder="横幅大标题" />
        </UFormGroup>
        <UFormGroup label="副标题">
          <UInput v-model="editing.subtitle" placeholder="辅助说明文字" />
        </UFormGroup>
        <UFormGroup label="背景图片 URL" required>
          <UInput v-model="editing.image" placeholder="https://..." />
          <div v-if="editing.image" class="mt-xs rounded-lg overflow-hidden border border-neutral-border-secondary">
            <img :src="editing.image" alt="预览" class="w-full h-40 object-cover" />
          </div>
        </UFormGroup>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="跳转链接">
              <UInput v-model="editing.link" placeholder="https:// 或相对路径" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="打开方式">
              <USelect v-model="editing.target">
                <option v-for="o in targetOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
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
            <UFormGroup label="排序（越小越靠前）">
              <UInput v-model.number="editing.sort" type="number" />
            </UFormGroup>
          </div>
          <div class="flex items-end">
            <UCheckbox v-model="editing.enabled" label="启用此横幅" class="mb-2" />
          </div>
        </div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="dialogOpen = false">取消</UButton>
        <UButton color="primary" @click="save">保存</UButton>
      </template>
    </UDialog>

    <UDialog v-model="previewOpen" title="横幅预览" size="3xl">
      <div v-if="previewItem" class="rounded-xl overflow-hidden aspect-[21/9] bg-gradient-to-br from-primary-500/20 to-nebula-blue/20">
        <img v-if="previewItem.image" :src="previewItem.image" :alt="previewItem.title" class="w-full h-full object-cover" />
      </div>
      <div v-if="previewItem" class="mt-md text-center">
        <h3 class="text-xl font-bold text-neutral-text-primary">{{ previewItem.title || '（无标题）' }}</h3>
        <p v-if="previewItem.subtitle" class="text-neutral-text-secondary mt-xs">{{ previewItem.subtitle }}</p>
        <a v-if="previewItem.link" :href="previewItem.link" :target="previewItem.target" class="inline-block mt-sm text-primary-500 hover:text-primary-400 underline-offset-2 underline decoration-dotted text-sm">
          访问链接 →
        </a>
      </div>
    </UDialog>
  </div>
</template>

<style scoped>
</style>
