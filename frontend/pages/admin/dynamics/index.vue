<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "动态/说说管理 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const visibilityFilter = ref<String>(String(route.query.visibility || "all"));

watch([() => route.query.page, () => route.query.q, () => route.query.visibility], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  visibilityFilter.value = String(route.query.visibility || "all");
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/dynamics", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    visibility: visibilityFilter.value !== "all" ? visibilityFilter.value : undefined,
  })),
  default: () => ({ items: [], total: 0, totalPages: 1 }),
  lazy: true,
  server: false,
});

const dialogOpen = ref(false);
const editing = ref<any>(null);
const deleting = ref<number | string | null>(null);
const imageInput = ref("");

const visibilityOptions = [
  { value: "public", label: "公开", color: "success" },
  { value: "friends", label: "好友可见", color: "info" },
  { value: "private", label: "仅自己", color: "warning" },
];

function getVisibilityMeta(v: string) {
  return visibilityOptions.find(o => o.value === v) || { label: v, color: "neutral" };
}

function openNew() {
  editing.value = {
    id: 0,
    content: "",
    images: [] as string[],
    location: "",
    visibility: "public",
    publishedAt: "",
  };
  dialogOpen.value = true;
}

function openEdit(item: any) {
  editing.value = structuredClone(item);
  if (!editing.value.images) editing.value.images = [];
  dialogOpen.value = true;
}

function addImage() {
  if (!imageInput.value.trim() || !editing.value) return;
  editing.value.images.push(imageInput.value.trim());
  imageInput.value = "";
}

function removeImage(idx: number) {
  editing.value.images.splice(idx, 1);
}

async function save() {
  try {
    const e = editing.value;
    if (e.id) {
      await apiPut(`/api/admin/dynamics/${e.id}`, e);
      toast.add({ title: "更新成功", color: "success" });
    } else {
      await apiPost("/api/admin/dynamics", e);
      toast.add({ title: "发布成功", color: "success" });
    }
    dialogOpen.value = false;
    editing.value = null;
    await refresh();
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "保存失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该动态？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/dynamics/${id}`);
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
      <h1 class="text-2xl font-bold text-neutral-text-primary">动态 / 说说管理</h1>
      <UButton color="primary" @click="openNew">
        <UIcon name="material-symbols:add-rounded" class="w-4 h-4 mr-1" />
        发布动态
      </UButton>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs"
      @submit.prevent="navigateTo({ path: '/admin/dynamics', query: { q: keyword || undefined, visibility: visibilityFilter !== 'all' ? visibilityFilter : undefined, page: 1 } })"
    >
      <UInput v-model="keyword" type="search" placeholder="搜索内容 / 位置" class="sm:flex-1" />
      <USelect v-model="visibilityFilter" class="sm:w-40">
        <option value="all">全部可见性</option>
        <option v-for="o in visibilityOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
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
              <th class="px-4 py-3 text-left font-medium">内容</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">图片 / 位置</th>
              <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">互动</th>
              <th class="px-4 py-3 text-left font-medium">可见性</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">发布时间</th>
              <th class="px-4 py-3 text-right font-medium w-36">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums align-top">{{ item.id }}</td>
              <td class="px-4 py-3 align-top min-w-[250px]">
                <p class="text-neutral-text-primary whitespace-pre-wrap line-clamp-4">{{ item.content }}</p>
              </td>
              <td class="px-4 py-3 hidden md:table-cell align-top">
                <div v-if="item.images && item.images.length" class="flex gap-1 flex-wrap mb-xs">
                  <div v-for="(img, i) in item.images.slice(0, 4)" :key="i" class="w-10 h-10 rounded bg-neutral-fill-hover overflow-hidden">
                    <img :src="img" class="w-full h-full object-cover" />
                  </div>
                  <span v-if="item.images.length > 4" class="w-10 h-10 rounded bg-neutral-fill-hover flex items-center justify-center text-xs text-neutral-text-tertiary">
                    +{{ item.images.length - 4 }}
                  </span>
                </div>
                <p v-if="item.location" class="text-xs text-neutral-text-tertiary inline-flex items-center gap-0.5">
                  <UIcon name="material-symbols:location-on-rounded" class="w-3 h-3" />
                  {{ item.location }}
                </p>
              </td>
              <td class="px-4 py-3 hidden lg:table-cell align-top text-xs">
                <p class="flex items-center gap-xs text-neutral-text-secondary">
                  <UIcon name="material-symbols:favorite-rounded" class="w-3.5 h-3.5 text-danger-400" />
                  {{ item.likes || 0 }}
                </p>
                <p class="flex items-center gap-xs text-neutral-text-secondary mt-1">
                  <UIcon name="material-symbols:chat-bubble-outline-rounded" class="w-3.5 h-3.5" />
                  {{ item.commentsCount || 0 }}
                </p>
              </td>
              <td class="px-4 py-3 align-top">
                <UBadge :color="getVisibilityMeta(item.visibility).color" variant="subtle">
                  {{ getVisibilityMeta(item.visibility).label }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell align-top tabular-nums">
                {{ item.publishedAt ? dayjs(item.publishedAt).format('YYYY-MM-DD HH:mm') : '—' }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap align-top">
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
                <UIcon name="material-symbols:dynamic-form-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无动态，发布第一条说说吧</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/dynamics', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 条</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/dynamics', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="dialogOpen" :title="editing?.id ? '编辑动态' : '发布动态'" size="2xl">
      <div v-if="editing" class="space-y-sm">
        <UFormGroup label="动态内容" required>
          <textarea
            v-model="editing.content"
            rows="5"
            placeholder="此刻的想法..."
            class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"
          />
        </UFormGroup>
        <UFormGroup label="图片列表（每行一个 URL，或逐个添加）">
          <div class="space-y-xs">
            <div v-for="(img, i) in editing.images" :key="i" class="flex items-center gap-xs">
              <div class="w-12 h-12 rounded bg-neutral-fill-hover overflow-hidden flex-shrink-0">
                <img v-if="img" :src="img" class="w-full h-full object-cover" />
              </div>
              <input :value="img" readonly class="flex-1 h-9 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-xs text-neutral-text-secondary" />
              <UButton size="xs" variant="ghost" color="danger" @click="removeImage(i)">
                <UIcon name="material-symbols:close-rounded" class="w-4 h-4" />
              </UButton>
            </div>
            <div class="flex gap-xs">
              <UInput v-model="imageInput" placeholder="粘贴图片 URL" @keyup.enter="addImage" />
              <UButton variant="ghost" @click="addImage">
                <UIcon name="material-symbols:add-photo-alternate-rounded" class="w-4 h-4 mr-1" />
                添加
              </UButton>
            </div>
          </div>
        </UFormGroup>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="位置（可选）">
              <UInput v-model="editing.location" placeholder="例如：上海外滩" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="可见性">
              <USelect v-model="editing.visibility">
                <option v-for="o in visibilityOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </USelect>
            </UFormGroup>
          </div>
          <div class="sm:col-span-2">
            <UFormGroup label="发布时间（留空为立即）">
              <UInput v-model="editing.publishedAt" type="datetime-local" />
            </UFormGroup>
          </div>
        </div>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="dialogOpen = false">取消</UButton>
        <UButton color="primary" @click="save">{{ editing?.id ? '保存' : '发布' }}</UButton>
      </template>
    </UDialog>
  </div>
</template>

<style scoped>
</style>
