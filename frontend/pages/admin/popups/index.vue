<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "弹窗/公告位管理 - Rosetta 后台" });
const { data, refresh } = await useFetch<any[]>("/api/admin/popups", {
  default: () => ([
    { id: 1, name: "春季更新公告", placement: "hero-banner", active: true, template: "markdown", content: "", startAt: "", endAt: "", frequency: "per_session" },
    { id: 2, name: "Cookie 合规", placement: "footer", active: true, template: "cookie", frequency: "per_7d" },
    { id: 3, name: "赞助提示", placement: "sidebar", active: false, template: "sponsor" },
  ]), lazy: true, server: false,
});
const editing = ref<any>(null);
function openNew() { editing.value = { id: 0, name: "", placement: "hero-banner", active: true, template: "markdown", content: "", startAt: "", endAt: "", frequency: "once" }; }
async function save() {
  try {
    const e = editing.value;
    if (e.id) await apiPut(`/api/admin/popups/${e.id}`, e);
    else await apiPost("/api/admin/popups", e);
    editing.value = null; await refresh();
  } catch (e: any) { alert(e?.message || "保存失败"); }
}
async function remove(id: any) {
  if (!confirm("删除该弹窗？")) return;
  try { await apiDelete(`/api/admin/popups/${id}`); await refresh(); }
  catch (e: any) { alert(e.message); }
}
const placements = [
  ["hero-banner", "首页 Hero 横幅"],
  ["sidebar", "侧栏卡片"],
  ["footer", "页脚条"],
  ["modal", "全屏模态（一次）"],
  ["toast", "气泡提示"],
];
const templates = [
  ["markdown", "Markdown 自由书写"],
  ["cookie", "Cookie 合规"],
  ["sponsor", "赞助卡片"],
  ["rss-cta", "订阅号召"],
  ["oobe-shortcut", "OOBE 入口"],
];
const freqs = [
  ["once", "每个浏览器一次"],
  ["per_session", "每次会话一次"],
  ["per_7d", "每 7 天一次"],
  ["always", "每次都显示"],
];
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-neutral-text-primary">弹窗 / 公告位</h1>
      <button @click="openNew" class="px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 inline-flex items-center gap-1 shadow-sm">
        <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新增位置
      </button>
    </header>

    <section v-if="editing" class="bg-neutral-bg-container border border-primary-500/40 rounded-2xl p-lg shadow-lg ring-4 ring-primary-500/10 max-w-3xl">
      <h3 class="font-semibold mb-sm text-neutral-text-primary">{{ editing.id ? '编辑' : '新增' }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-sm text-sm">
        <label class="sm:col-span-3"><span class="text-xs text-neutral-text-tertiary mb-1 block">名称（内部）</span>
          <input v-model="editing.name" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">位置</span>
          <select v-model="editing.placement" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
            <option v-for="[v,l] in placements" :key="v" :value="v">{{ l }}</option>
          </select>
        </label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">模板</span>
          <select v-model="editing.template" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
            <option v-for="[v,l] in templates" :key="v" :value="v">{{ l }}</option>
          </select>
        </label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">频率</span>
          <select v-model="editing.frequency" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
            <option v-for="[v,l] in freqs" :key="v" :value="v">{{ l }}</option>
          </select>
        </label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">开始</span>
          <input v-model="editing.startAt" type="datetime-local" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">结束</span>
          <input v-model="editing.endAt" type="datetime-local" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label class="inline-flex items-center gap-xs cursor-pointer self-end pb-1 select-none">
          <input v-model="editing.active" type="checkbox" class="w-4 h-4 text-primary-500"/> 启用
        </label>
        <label class="sm:col-span-3"><span class="text-xs text-neutral-text-tertiary mb-1 block">内容（Markdown 或 HTML）</span>
          <textarea v-model="editing.content" rows="5" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary resize-none font-mono text-xs"/></label>
      </div>
      <div class="mt-md flex justify-end gap-xs">
        <button @click="editing = null" class="px-4 h-9 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm">取消</button>
        <button @click="save" class="px-4 h-9 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400">保存</button>
      </div>
    </section>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-md">
      <div v-for="p in (data||[])" :key="p.id"
        class="bg-neutral-bg-container border border-neutral-border-secondary rounded-xl p-md hover:shadow-sm transition-all"
        :class="!p.active ? 'opacity-70' : ''">
        <div class="flex items-start justify-between">
          <h3 class="font-semibold text-neutral-text-primary">{{ p.name }}</h3>
          <label class="inline-flex items-center gap-xs cursor-pointer select-none">
            <input v-model="p.active" type="checkbox" class="w-4 h-4 text-primary-500"/>
            <span class="text-[10px] text-neutral-text-tertiary">{{ p.active ? '已启用' : '停用' }}</span>
          </label>
        </div>
        <div class="mt-xs flex flex-wrap gap-xs text-xs">
          <span v-for="[v,l] in placements" :key="v" v-show="p.placement === v" class="px-2 py-0.5 rounded bg-primary-500/10 text-primary-500 font-medium">{{ l }}</span>
          <span class="px-2 py-0.5 rounded bg-neutral-fill-hover text-neutral-text-secondary">模板: {{ p.template }}</span>
          <span class="px-2 py-0.5 rounded bg-neutral-fill-hover text-neutral-text-secondary">{{ p.frequency }}</span>
        </div>
        <p v-if="p.content" class="mt-sm text-xs text-neutral-text-secondary line-clamp-3 whitespace-pre-wrap">{{ p.content }}</p>
        <div class="mt-md pt-sm border-t border-neutral-border-secondary flex items-center justify-between text-xs">
          <p class="text-neutral-text-quaternary">{{ p.startAt || p.endAt ? `${p.startAt || '—'} ~ ${p.endAt || '—'}` : '无时间限制' }}</p>
          <div class="space-x-xs">
            <button @click="editing = structuredClone(p)" class="text-primary-500 hover:text-primary-400 inline-flex items-center gap-0.5">
              <Icon name="material-symbols:edit-rounded" class="w-3.5 h-3.5"/>编辑
            </button>
            <button @click="remove(p.id)" class="text-danger-500 hover:text-danger-400 inline-flex items-center gap-0.5">
              <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
