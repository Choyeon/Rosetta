<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "通知中心 - Rosetta 后台" });
const { data, refresh } = await useFetch<any[]>("/api/admin/notifications", {
  default: () => ([
    { id: 1, title: "欢迎使用 Rosetta", level: "info", type: "system", content: "已完成站点初始化。", target: "/admin", createdAt: "2026-03-26", read: false },
    { id: 2, title: "新版本可用", level: "success", type: "system", content: "v0.3.0 已发布，请在 Releases 查看。", createdAt: "2026-03-25", read: true },
    { id: 3, title: "检测到异常登录", level: "warning", type: "security", content: "IP 203.0.113.42 登录失败 5 次。", createdAt: "2026-03-24", read: false },
  ]),
  lazy: true, server: false,
});
const editing = ref<any>(null);
function openNew() { editing.value = { id: 0, title: "", content: "", level: "info", type: "broadcast", target: "", sendNow: false }; }
async function save() {
  try {
    const e = editing.value;
    if (e.id) await apiPut(`/api/admin/notifications/${e.id}`, e);
    else await apiPost("/api/admin/notifications", e);
    editing.value = null; await refresh();
  } catch (e: any) { alert(e?.message || "发送失败"); }
}
async function toggleRead(n: any) { try { n.read = !n.read; await apiPut(`/api/admin/notifications/${n.id}`, { read: n.read }); } catch (e:any) { n.read = !n.read; alert(e.message); } }
async function remove(id: any) { try { await apiDelete(`/api/admin/notifications/${id}`); await refresh(); } catch (e:any) { alert(e.message); } }
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-neutral-text-primary">通知中心</h1>
      <button @click="openNew" class="px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 inline-flex items-center gap-1 shadow-sm">
        <Icon name="material-symbols:campaign-rounded" class="w-4 h-4"/>广播新通知
      </button>
    </header>

    <section v-if="editing" class="bg-neutral-bg-container border border-primary-500/40 rounded-2xl p-lg shadow-lg ring-4 ring-primary-500/10 max-w-2xl">
      <h3 class="font-semibold mb-sm text-neutral-text-primary">{{ editing.id ? '编辑' : '新建广播' }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm text-sm">
        <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">标题 *</span>
          <input v-model="editing.title" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">级别</span>
          <select v-model="editing.level" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
            <option value="info">信息</option><option value="success">成功</option><option value="warning">警告</option><option value="danger">重要</option>
          </select>
        </label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">类型</span>
          <select v-model="editing.type" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
            <option value="broadcast">全站广播</option><option value="system">系统</option><option value="security">安全</option><option value="feature">功能更新</option>
          </select>
        </label>
        <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">目标路由（点击跳转）</span>
          <input v-model="editing.target" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary" placeholder="/admin/posts/..."/></label>
        <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">内容</span>
          <textarea v-model="editing.content" rows="3" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary resize-none"/></label>
        <label class="inline-flex items-center gap-xs cursor-pointer select-none"><input v-model="editing.sendNow" type="checkbox" class="w-4 h-4 text-primary-500"/>立即推送（邮件 / 站内 / 飞书）</label>
      </div>
      <div class="mt-md flex justify-end gap-xs">
        <button @click="editing = null" class="px-4 h-9 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm">取消</button>
        <button @click="save" class="px-4 h-9 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400">{{ editing.sendNow ? '发送' : '保存' }}</button>
      </div>
    </section>

    <div class="space-y-xs">
      <article
        v-for="n in ((data||[]))"
        :key="n.id"
        class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-md flex items-start gap-sm hover:shadow-sm transition-all"
        :class="n.read ? 'opacity-80' : ''"
      >
        <div class="w-10 h-10 shrink-0 rounded-lg flex items-center justify-center"
          :class="{
            'bg-info-500/10 text-info-500': n.level === 'info',
            'bg-success-500/10 text-success-500': n.level === 'success',
            'bg-warning-500/10 text-warning-500': n.level === 'warning',
            'bg-danger-500/10 text-danger-500': n.level === 'danger',
          }">
          <Icon name="material-symbols:notifications-active-rounded" class="w-5 h-5"/>
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-xs flex-wrap">
            <h3 class="font-semibold text-neutral-text-primary">{{ n.title }}</h3>
            <span class="text-[10px] px-2 py-0.5 rounded bg-neutral-fill-hover text-neutral-text-tertiary font-medium">{{ n.type }}</span>
            <span v-if="!n.read" class="text-[10px] px-2 py-0.5 rounded bg-primary-500 text-white font-semibold">NEW</span>
          </div>
          <p class="mt-xs text-sm text-neutral-text-secondary line-clamp-2">{{ n.content }}</p>
          <p class="mt-xs text-xs text-neutral-text-quaternary tabular-nums">{{ new Date(n.createdAt||'').toLocaleString() || '—' }}</p>
        </div>
        <div class="flex flex-col items-end gap-xs shrink-0">
          <button @click="toggleRead(n)" class="text-xs text-neutral-text-tertiary hover:text-primary-500 inline-flex items-center gap-0.5">
            <Icon :name="n.read ? 'material-symbols:mark-email-read-rounded' : 'material-symbols:drafts-rounded'" class="w-3.5 h-3.5"/>
            {{ n.read ? '标为未读' : '标为已读' }}
          </button>
          <button @click="editing = structuredClone(n)" class="text-xs text-primary-500 hover:text-primary-400 inline-flex items-center gap-0.5">
            <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5"/>编辑
          </button>
          <button @click="remove(n.id)" class="text-xs text-danger-500 hover:text-danger-400 inline-flex items-center gap-0.5">
            <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
          </button>
        </div>
      </article>
      <p v-if="(data||[]).length === 0" class="py-xl text-center text-sm text-neutral-text-tertiary">暂无通知。</p>
    </div>
  </div>
</template>
