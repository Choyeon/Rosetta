<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "友情链接 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const groupFilter = ref<String>(String(route.query.group || "all"));
const approvedFilter = ref<String>(String(route.query.approved || "all"));

watch([() => route.query.page, () => route.query.q, () => route.query.group, () => route.query.approved], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  groupFilter.value = String(route.query.group || "all");
  approvedFilter.value = String(route.query.approved || "all");
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/friends", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    group: groupFilter.value !== "all" ? groupFilter.value : undefined,
    approved: approvedFilter.value !== "all" ? approvedFilter.value : undefined,
  })),
  default: () => ({ items: [], total: 0, totalPages: 1, pendingCount: 0, groups: [] as string[] }),
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
    url: "",
    avatar: "",
    description: "",
    group: "默认",
    sort: 0,
    approved: true,
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
      await apiPut(`/api/admin/friends/${e.id}`, e);
      toast.add({ title: "更新成功", color: "success" });
    } else {
      await apiPost("/api/admin/friends", e);
      toast.add({ title: "创建成功", color: "success" });
    }
    dialogOpen.value = false;
    editing.value = null;
    await refresh();
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "保存失败", color: "danger" });
  }
}

async function toggleApproved(item: any) {
  try {
    const newState = !item.approved;
    await apiPatch(`/api/admin/friends/${item.id}`, { approved: newState });
    item.approved = newState;
    toast.add({ title: newState ? "已通过" : "已取消通过", color: "success" });
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "操作失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该友链？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/friends/${id}`);
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
      <div>
        <h1 class="text-2xl font-bold text-neutral-text-primary">友情链接</h1>
        <p v-if="data?.pendingCount" class="text-sm text-warning-500 mt-1">
          <UIcon name="material-symbols:group-add-rounded" class="w-4 h-4 inline mr-0.5" />
          {{ data.pendingCount }} 个申请等待审核
        </p>
      </div>
      <UButton color="primary" @click="openNew">
        <UIcon name="material-symbols:add-rounded" class="w-4 h-4 mr-1" />
        添加友链
      </UButton>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs flex-wrap"
      @submit.prevent="navigateTo({ path: '/admin/friends', query: { q: keyword || undefined, group: groupFilter !== 'all' ? groupFilter : undefined, approved: approvedFilter !== 'all' ? approvedFilter : undefined, page: 1 } })"
    >
      <UInput v-model="keyword" type="search" placeholder="搜索名称 / URL / 描述" class="sm:flex-1 min-w-[200px]" />
      <USelect v-model="groupFilter" class="sm:w-36">
        <option value="all">全部分组</option>
        <option v-for="g in (data?.groups || [])" :key="g" :value="g">{{ g }}</option>
      </USelect>
      <USelect v-model="approvedFilter" class="sm:w-36">
        <option value="all">全部状态</option>
        <option value="true">已通过</option>
        <option value="false">待审核</option>
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
              <th class="px-4 py-3 text-left font-medium">站点</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">描述</th>
              <th class="px-4 py-3 text-left font-medium hidden lg:table-cell">分组</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">排序</th>
              <th class="px-4 py-3 text-left font-medium">审核</th>
              <th class="px-4 py-3 text-right font-medium w-44">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums">{{ item.id }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-sm">
                  <div class="w-10 h-10 rounded-xl bg-neutral-fill-hover overflow-hidden flex-shrink-0 border border-neutral-border-secondary">
                    <img v-if="item.avatar" :src="item.avatar" :alt="item.name" class="w-full h-full object-cover" />
                    <div v-else class="w-full h-full flex items-center justify-center">
                      <UIcon name="material-symbols:language-rounded" class="w-5 h-5 text-neutral-text-tertiary" />
                    </div>
                  </div>
                  <div class="min-w-0">
                    <a :href="item.url" target="_blank" class="font-medium text-neutral-text-primary hover:text-primary-500 line-clamp-1 block">
                      {{ item.name }}
                    </a>
                    <p class="text-xs text-neutral-text-tertiary font-mono truncate max-w-[200px]">{{ item.url }}</p>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 hidden md:table-cell text-xs text-neutral-text-secondary line-clamp-2 max-w-[250px]">
                {{ item.description || '—' }}
              </td>
              <td class="px-4 py-3 hidden lg:table-cell">
                <UBadge variant="subtle" color="info">{{ item.group || '默认' }}</UBadge>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell tabular-nums">{{ item.sort ?? 0 }}</td>
              <td class="px-4 py-3">
                <button @click="toggleApproved(item)" class="cursor-pointer">
                  <UBadge :color="item.approved ? 'success' : 'warning'" variant="subtle">
                    {{ item.approved ? '已通过' : '待审核' }}
                  </UBadge>
                </button>
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
              <td colspan="7" class="px-4 py-12 text-center text-neutral-text-tertiary text-sm">
                <UIcon name="material-symbols:link-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无友链</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/friends', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 条</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/friends', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="dialogOpen" :title="editing?.id ? '编辑友链' : '添加友链'">
      <div v-if="editing" class="space-y-sm">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <div>
            <UFormGroup label="站点名称" required>
              <UInput v-model="editing.name" placeholder="例如：Rosetta Blog" />
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="站点 URL" required>
              <UInput v-model="editing.url" placeholder="https://" />
            </UFormGroup>
          </div>
        </div>
        <UFormGroup label="头像 / Logo URL">
          <div class="flex gap-xs">
            <UInput v-model="editing.avatar" placeholder="https://..." class="flex-1" />
            <div v-if="editing.avatar" class="w-10 h-10 rounded-lg bg-neutral-fill-hover overflow-hidden border border-neutral-border-secondary">
              <img :src="editing.avatar" class="w-full h-full object-cover" />
            </div>
          </div>
        </UFormGroup>
        <UFormGroup label="站点描述">
          <textarea
            v-model="editing.description"
            rows="2"
            placeholder="一句话介绍..."
            class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"
          />
        </UFormGroup>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-sm">
          <div>
            <UFormGroup label="分组">
              <UInput v-model="editing.group" list="group-suggest" placeholder="默认" />
              <datalist id="group-suggest">
                <option v-for="g in (data?.groups || [])" :key="g" :value="g" />
              </datalist>
            </UFormGroup>
          </div>
          <div>
            <UFormGroup label="排序（越小越前）">
              <UInput v-model.number="editing.sort" type="number" />
            </UFormGroup>
          </div>
          <div class="flex items-end">
            <UCheckbox v-model="editing.approved" label="立即通过审核" class="mb-2" />
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
