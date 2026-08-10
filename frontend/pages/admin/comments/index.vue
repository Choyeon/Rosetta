<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "评论审核 - Rosetta 后台" });
const toast = useToast();
const route = useRoute();

const page = ref(parseInt(String(route.query.page || 1), 10) || 1);
const pageSize = 20;
const keyword = ref(String(route.query.q || ""));
const statusFilter = ref<String>(String(route.query.status || "pending"));

watch([() => route.query.page, () => route.query.q, () => route.query.status], () => {
  page.value = parseInt(String(route.query.page || 1), 10) || 1;
  keyword.value = String(route.query.q || "");
  statusFilter.value = String(route.query.status || "pending");
});

const { data, pending, refresh } = await useFetch<any>("/api/admin/comments", {
  query: computed(() => ({
    page: page.value,
    pageSize,
    keyword: keyword.value,
    status: statusFilter.value,
  })),
  default: () => ({ items: [], total: 0, totalPages: 1, pendingCount: 0 }),
  lazy: true,
  server: false,
});

const deleting = ref<number | string | null>(null);
const replyOpen = ref(false);
const replyTarget = ref<any>(null);
const replyContent = ref("");

const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: "待审核", color: "warning" },
  approved: { label: "已通过", color: "success" },
  rejected: { label: "已拒绝", color: "danger" },
  spam: { label: "垃圾", color: "neutral" },
};

function openReply(item: any) {
  replyTarget.value = item;
  replyContent.value = "";
  replyOpen.value = true;
}

async function submitReply() {
  if (!replyContent.value.trim() || !replyTarget.value) return;
  try {
    await apiPost(`/api/admin/comments/${replyTarget.value.id}/reply`, { content: replyContent.value });
    toast.add({ title: "回复成功", color: "success" });
    replyOpen.value = false;
    replyTarget.value = null;
    replyContent.value = "";
    await refresh();
  } catch (err: any) {
    toast.add({ title: "回复失败", description: err?.message || "回复失败", color: "danger" });
  }
}

async function updateStatus(id: number | string, newStatus: string) {
  try {
    await apiPatch(`/api/admin/comments/${id}`, { status: newStatus });
    toast.add({ title: `已${statusMap[newStatus]?.label || '更新'}`, color: "success" });
    await refresh();
  } catch (err: any) {
    toast.add({ title: "操作失败", description: err?.message || "操作失败", color: "danger" });
  }
}

async function remove(id: number | string) {
  if (!confirm("确定删除该评论？此操作不可撤销。")) return;
  deleting.value = id;
  try {
    await apiDelete(`/api/admin/comments/${id}`);
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
        <h1 class="text-2xl font-bold text-neutral-text-primary">评论审核</h1>
        <p v-if="data?.pendingCount" class="text-sm text-warning-500 mt-1">
          <UIcon name="material-symbols:error-circle-rounded" class="w-4 h-4 inline mr-0.5" />
          当前有 {{ data.pendingCount }} 条评论等待审核
        </p>
      </div>
    </header>

    <form
      class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-sm flex flex-col sm:flex-row gap-xs"
      @submit.prevent="navigateTo({ path: '/admin/comments', query: { q: keyword || undefined, status: statusFilter, page: 1 } })"
    >
      <UInput v-model="keyword" type="search" placeholder="搜索作者 / 邮箱 / 内容" class="sm:flex-1" />
      <USelect v-model="statusFilter" class="sm:w-40">
        <option value="all">全部</option>
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
              <th class="px-4 py-3 text-left font-medium">作者</th>
              <th class="px-4 py-3 text-left font-medium">评论内容</th>
              <th class="px-4 py-3 text-left font-medium hidden md:table-cell">所属文章</th>
              <th class="px-4 py-3 text-left font-medium">状态</th>
              <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">时间</th>
              <th class="px-4 py-3 text-right font-medium w-64">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="item in (data?.items || [])" :key="item.id" class="hover:bg-neutral-fill-hover/40 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-neutral-text-tertiary tabular-nums align-top">{{ item.id }}</td>
              <td class="px-4 py-3 align-top">
                <p class="font-medium text-neutral-text-primary">{{ item.author || '匿名' }}</p>
                <p v-if="item.email" class="text-xs text-neutral-text-tertiary mt-0.5">{{ item.email }}</p>
              </td>
              <td class="px-4 py-3 align-top min-w-[250px]">
                <p class="text-neutral-text-secondary whitespace-pre-wrap line-clamp-3">{{ item.content }}</p>
              </td>
              <td class="px-4 py-3 hidden md:table-cell align-top">
                <span v-if="item.postTitle" class="text-xs text-neutral-text-secondary line-clamp-2 block">{{ item.postTitle }}</span>
                <span v-else class="text-xs text-neutral-text-quaternary">—</span>
              </td>
              <td class="px-4 py-3 align-top">
                <UBadge :color="statusMap[item.status]?.color || 'neutral'" variant="subtle">
                  {{ statusMap[item.status]?.label || item.status }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-xs text-neutral-text-tertiary hidden sm:table-cell align-top tabular-nums">
                {{ item.createdAt ? dayjs(item.createdAt).format('YYYY-MM-DD HH:mm') : '—' }}
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap align-top">
                <div class="flex flex-wrap justify-end gap-1">
                  <template v-if="item.status === 'pending'">
                    <UButton size="xs" variant="ghost" color="success" @click="updateStatus(item.id, 'approved')">
                      <UIcon name="material-symbols:check-rounded" class="w-3.5 h-3.5 mr-0.5" />
                      通过
                    </UButton>
                    <UButton size="xs" variant="ghost" color="danger" @click="updateStatus(item.id, 'rejected')">
                      <UIcon name="material-symbols:close-rounded" class="w-3.5 h-3.5 mr-0.5" />
                      拒绝
                    </UButton>
                  </template>
                  <template v-else-if="item.status === 'approved'">
                    <UButton size="xs" variant="ghost" color="warning" @click="updateStatus(item.id, 'pending')">
                      <UIcon name="material-symbols:pending-rounded" class="w-3.5 h-3.5 mr-0.5" />
                      撤回
                    </UButton>
                  </template>
                  <UButton size="xs" variant="ghost" color="primary" @click="openReply(item)">
                    <UIcon name="material-symbols:reply-rounded" class="w-3.5 h-3.5 mr-0.5" />
                    回复
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
                </div>
              </td>
            </tr>
            <tr v-if="!pending && data?.items?.length === 0">
              <td colspan="7" class="px-4 py-12 text-center text-neutral-text-tertiary text-sm">
                <UIcon name="material-symbols:chat-bubble-outline-rounded" class="w-12 h-12 mx-auto mb-2 text-neutral-text-quaternary" />
                <p>暂无评论</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="(data?.totalPages || 1) > 1" class="flex items-center justify-between px-4 py-3 border-t border-neutral-border-secondary text-sm">
        <NuxtLink
          v-if="page > 1"
          :to="{ path: '/admin/comments', query: { ...route.query, page: page - 1 } }"
          class="px-3 py-1.5 rounded bg-neutral-fill-hover hover:bg-neutral-fill-active"
        >上一页</NuxtLink>
        <span v-else />
        <span class="text-neutral-text-tertiary">{{ page }} / {{ data?.totalPages || 1 }} · 共 {{ data?.total || 0 }} 条</span>
        <NuxtLink
          v-if="page < (data?.totalPages || 1)"
          :to="{ path: '/admin/comments', query: { ...route.query, page: page + 1 } }"
          class="px-3 py-1.5 rounded bg-primary-500 text-white hover:bg-primary-400"
        >下一页</NuxtLink>
      </div>
    </div>

    <UDialog v-model="replyOpen" title="回复评论" size="lg">
      <div v-if="replyTarget" class="space-y-sm">
        <div class="bg-neutral-fill-hover rounded-lg p-sm">
          <p class="text-xs text-neutral-text-tertiary mb-xs">
            <span class="font-medium text-neutral-text-secondary">{{ replyTarget.author || '匿名' }}</span>
            <span class="ml-xs">{{ replyTarget.createdAt ? dayjs(replyTarget.createdAt).format('YYYY-MM-DD HH:mm') : '' }}</span>
          </p>
          <p class="text-sm text-neutral-text-secondary whitespace-pre-wrap">{{ replyTarget.content }}</p>
        </div>
        <UFormGroup label="回复内容" required>
          <textarea
            v-model="replyContent"
            rows="4"
            placeholder="输入回复内容..."
            class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"
          />
        </UFormGroup>
      </div>
      <template #footer>
        <UButton variant="ghost" @click="replyOpen = false">取消</UButton>
        <UButton color="primary" @click="submitReply">发送回复</UButton>
      </template>
    </UDialog>
  </div>
</template>

<style scoped>
</style>
