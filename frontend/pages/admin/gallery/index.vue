<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "图库照片管理 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 30;
const keyword = ref(String(route.query.q || ""));
const albumFilter = ref<string>(String(route.query.album || ""));

watch([() => route.query.page, () => route.query.q, () => route.query.album], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  albumFilter.value = String(route.query.album || "");
});

const { data: albumsData } = await useFetch<any>("/api/admin/albums/all", {
  default: () => ([] as any[]),
  lazy: true,
  server: false,
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/gallery", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    albumId: albumFilter.value || undefined,
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

function openNew() {
  editing.value = {
    id: 0,
    albumId: albumFilter.value ? parseInt(albumFilter.value) : null,
    title: "",
    url: "",
    thumbnail: "",
    size: 0,
    width: 0,
    height: 0,
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

function formatSize(bytes: number) {
  if (!bytes) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++; }
  return `${val.toFixed(val >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
}

async function save() {
  try {
    const e = editing.value;
    if (e.id) {
      await apiPut(`/api/admin/gallery/${e.id}`, e);
      toast.add({ title: "更新成功", color: "success" });
    } else {
      await apiPost("/api/admin/gallery", e);
      toast.add({ title: "上传成功", color: "success" });
    }
    dialogOpen.value = false;
    editing.value = null;
    await refresh();
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "保存失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该照片？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/gallery/${id}`);
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
      <h1 class="text-2xl font-bold text-neutral-text-primary">图库照片管理</h1>
      <UButton color="primary" @click="openNew">
        <UIcon name="material-symbols:add-a-photo-rounded" class="w-4 h-4 mr-1" />
        添加照片
      </UButton>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs"
      @submit.prevent="navigateTo({ path: '/admin/gallery', query: { q: keyword || undefined, album: albumFilter || undefined, page: 1 } })"
    >
      <UInput v-model="keyword" type="search" placeholder="搜索照片标题" class="sm:flex-1" />
      <USelect v-model="albumFilter" class="sm:w-48">
        <option value="">全部相册</option>
        <option v-for="a in (albumsData || [])" :key="a.id" :value="String(a.id)">{{ a.name }}</option>
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
              <th class="px-4 py-3 text-left font-medium">缩略图</th>
              <th class="px-4 py-3 text-left font-medium">标题 / 相册</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">尺寸</th>
              <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">大小</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">上传时间</th>
              <th class="px-4 py-3 text-right font-medium w-44">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums">{{ item.id }}</td>
              <td class="px-4 py-3">
                <button @click="openPreview(item)" class="w-16 h-16 rounded-lg overflow-hidden bg-neutral-fill-hover block">
                  <img :src="item.thumbnail || item.url" :alt="item.title" class="w-full h-full object-cover" />
                </button>
              </td>
              <td class="px-4 py-3 min-w-[200px]">
                <p class="font-medium text-neutral-text-primary">{{ item.title || '（未命名）' }}</p>
                <p v-if="item.albumId" class="text-xs text-primary-500 mt-0.5 inline-flex items-center gap-0.5">
                  <UIcon name="material-symbols:photo-album-rounded" class="w-3 h-3" />
                  {{ (albumsData || []).find(a => a.id === item.albumId)?.name || `相册 #${item.albumId}` }}
                </p>
              </td>
              <td class="px-4 py-3 hidden md:table-cell text-xs text-neutral-text-secondary tabular-nums">
                {{ item.width && item.height ? `${item.width} × ${item.height}` : '—' }}
              </td>
              <td class="px-4 py-3 hidden lg:table-cell text-xs text-neutral-text-secondary tabular-nums">
                {{ formatSize(item.size) }}
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell tabular-nums">
                {{ item.uploadedAt ? dayjs(item.uploadedAt).format('YYYY-MM-DD HH:mm') : '—' }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <UButton size="xs" variant="ghost" color="neutral" class="mr-1" @click="openPreview(item)">
                  <UIcon name="material-symbols:visibility-rounded" class="w-3.5 h-3.5 mr-0.5" />
                  查看
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
              <td colspan="7" class="px-4 py-12 text-center text-neutral-text-tertiary text-sm">
                <UIcon name="material-symbols:collections-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无照片</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/gallery', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 张</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/gallery', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="dialogOpen" :title="editing?.id ? '编辑照片' : '添加照片'" size="2xl">
      <div v-if="editing" class="space-y-sm">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="所属相册">
              <USelect v-model="editing.albumId">
                <option :value="null">不指定相册</option>
                <option v-for="a in (albumsData || [])" :key="a.id" :value="a.id">{{ a.name }}</option>
              </USelect>
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="照片标题">
              <UInput v-model="editing.title" placeholder="给照片起个名字" />
            </UFormGroup>
          </div>
        </div>
        <UFormGroup label="原图 URL" required>
          <UInput v-model="editing.url" placeholder="https://..." @change="() => { if (!editing.thumbnail) editing.thumbnail = editing.url }" />
        </UFormGroup>
        <UFormGroup label="缩略图 URL（留空复用原图）">
          <UInput v-model="editing.thumbnail" placeholder="https://..." />
        </UFormGroup>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-sm">
          <div>
            <UFormGroup label="文件大小（字节）">
              <UInput v-model.number="editing.size" type="number" placeholder="可选" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="宽度 px">
              <UInput v-model.number="editing.width" type="number" placeholder="可选" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="高度 px">
              <UInput v-model.number="editing.height" type="number" placeholder="可选" />
            </UFormGroup>
          </div>
        </div>
        <div v-if="editing.url" class="rounded-lg overflow-hidden border border-neutral-border-secondary">
          <img :src="editing.url" alt="预览" class="w-full max-h-60 object-contain bg-neutral-bg-layout" />
        </div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="dialogOpen = false">取消</UButton>
        <UButton color="primary" @click="save">保存</UButton>
      </template>
    </UDialog>

    <UDialog v-model="previewOpen" title="照片预览" size="3xl">
      <div v-if="previewItem" class="flex justify-center">
        <img :src="previewItem.url" :alt="previewItem.title" class="max-w-full max-h-[70vh] rounded-lg object-contain" />
      </div>
      <div v-if="previewItem" class="mt-md text-center">
        <h3 class="font-semibold text-neutral-text-primary">{{ previewItem.title || '（未命名）' }}</h3>
        <p class="text-xs text-neutral-text-tertiary mt-xs tabular-nums">
          {{ previewItem.width && previewItem.height ? `${previewItem.width} × ${previewItem.height}` : '' }}
          {{ previewItem.size ? ` · ${formatSize(previewItem.size)}` : '' }}
          {{ previewItem.uploadedAt ? ` · 上传于 ${dayjs(previewItem.uploadedAt).format('YYYY-MM-DD')}` : '' }}
        </p>
      </div>
    </UDialog>
  </div>
</template>

<style scoped>
</style>
