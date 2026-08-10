<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "相册管理 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const publishedFilter = ref<String>(String(route.query.published || "all"));

watch([() => route.query.page, () => route.query.q, () => route.query.published], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  publishedFilter.value = String(route.query.published || "all");
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/albums", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    published: publishedFilter.value !== "all" ? publishedFilter.value : undefined,
  })),
  default: () => ({ items: [], total: 0, totalPages: 1 }),
  lazy: true,
  server: false,
});

const dialogOpen = ref(false);
const editing = ref<any>(null);
const deleting = ref<number | string | null>(null);

function openNew() {
  editing.value = {
    id: 0,
    name: "",
    slug: "",
    description: "",
    cover: "",
    order: 0,
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
      await apiPut(`/api/admin/albums/${e.id}`, e);
      toast.add({ title: "更新成功", description: `相册「${e.name}」已更新`, color: "success" });
    } else {
      await apiPost("/api/admin/albums", e);
      toast.add({ title: "创建成功", description: `相册「${e.name}」已创建`, color: "success" });
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
    await apiPatch(`/api/admin/albums/${item.id}`, { published: newState });
    item.published = newState;
    toast.add({ title: "状态已更新", color: "success" });
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "状态切换失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该相册？相册内的照片不会被删除。此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/albums/${id}`);
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
      <h1 class="text-2xl font-bold text-neutral-text-primary">相册管理</h1>
      <UButton color="primary" @click="openNew">
        <UIcon name="material-symbols:add-rounded" class="w-4 h-4 mr-1" />
        新建相册
      </UButton>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs"
      @submit.prevent="navigateTo({ path: '/admin/albums', query: { q: keyword || undefined, published: publishedFilter !== 'all' ? publishedFilter : undefined, page: 1 } })"
    >
      <UInput
        v-model="keyword"
        type="search"
        placeholder="搜索相册名称 / slug / 描述"
        class="sm:flex-1"
      />
      <USelect v-model="publishedFilter" class="sm:w-40">
        <option value="all">全部状态</option>
        <option value="true">已发布</option>
        <option value="false">未发布</option>
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
              <th class="px-4 py-3 text-left font-medium">封面</th>
              <th class="px-4 py-3 text-left font-medium">相册信息</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">排序</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">照片数</th>
              <th class="px-4 py-3 text-left font-medium">状态</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">创建时间</th>
              <th class="px-4 py-3 text-right font-medium w-36">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums">{{ item.id }}</td>
              <td class="px-4 py-3">
                <div v-if="item.cover" class="w-14 h-14 rounded-lg overflow-hidden bg-neutral-fill-hover">
                  <img :src="item.cover" :alt="item.name" class="w-full h-full object-cover" />
                </div>
                <div v-else class="w-14 h-14 rounded-lg bg-neutral-fill-hover flex items-center justify-center">
                  <UIcon name="material-symbols:photo-album-rounded" class="w-6 h-6 text-neutral-text-tertiary" />
                </div>
              </td>
              <td class="px-4 py-3 min-w-[200px]">
                <p class="font-medium text-neutral-text-primary">{{ item.name }}</p>
                <p class="text-xs font-mono text-neutral-text-tertiary mt-0.5">/{{ item.slug || item.id }}</p>
                <p v-if="item.description" class="text-xs text-neutral-text-secondary mt-1 line-clamp-1">{{ item.description }}</p>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden md:table-cell tabular-nums">{{ item.order ?? 0 }}</td>
              <td class="px-4 py-3 text-xs hidden sm:table-cell">
                <UBadge variant="subtle" color="primary">{{ item.photosCount || 0 }} 张</UBadge>
              </td>
              <td class="px-4 py-3">
                <button @click="togglePublished(item)" class="cursor-pointer">
                  <UBadge :color="item.published ? 'success' : 'neutral'" variant="subtle">
                    {{ item.published ? '已发布' : '未发布' }}
                  </UBadge>
                </button>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell tabular-nums">
                {{ item.createdAt ? dayjs(item.createdAt).format('YYYY-MM-DD HH:mm') : '—' }}
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
                <UIcon name="material-symbols:photo-album-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无相册，点击右上角「新建相册」开始创建</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/albums', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 条</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/albums', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="dialogOpen" :title="editing?.id ? '编辑相册' : '新建相册'">
      <div v-if="editing" class="space-y-sm">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="相册名称" required>
              <UInput v-model="editing.name" placeholder="例如：2024 日本之旅" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="Slug">
              <UInput v-model="editing.slug" placeholder="URL 友好标识，留空自动生成" />
            </UFormGroup>
          </div>
        </div>
        <UFormGroup label="描述">
          <textarea
            v-model="editing.description"
            rows="3"
            placeholder="相册简介..."
            class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"
          />
        </UFormGroup>
        <UFormGroup label="封面图 URL">
          <UInput v-model="editing.cover" placeholder="https://..." />
        </UFormGroup>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="排序（数字越小越靠前）">
              <UInput v-model.number="editing.order" type="number" />
            </UFormGroup>
          </div>
          <div class="flex items-end">
            <UCheckbox v-model="editing.published" label="发布此相册" class="mb-2" />
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
