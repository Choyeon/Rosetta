<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "定时任务 - Rosetta 后台" });
interface Job { id: number | string; name: string; cron: string; last?: string; next?: string; status: "running" | "idle" | "error"; lastError?: string; count?: number }
const jobs = ref<Job[]>([
  { id: 1, name: "生成 RSS / Sitemap", cron: "0 * * * *", last: "2026-03-26 10:00", next: "2026-03-26 11:00", status: "idle", count: 1382 },
  { id: 2, name: "清理回收站（30 天）", cron: "0 3 * * 0", last: "2026-03-24 03:00", next: "2026-03-31 03:00", status: "running", count: 12 },
  { id: 3, name: "搜索引擎提交（已发布）", cron: "15 */2 * * *", last: "2026-03-26 08:15", next: "2026-03-26 10:15", status: "idle", count: 402 },
  { id: 4, name: "备份数据库 + 媒体", cron: "30 4 * * *", last: "2026-03-26 04:30", next: "2026-03-27 04:30", status: "error", lastError: "S3 超时：bucket rosetta-backups connect ETIMEDOUT" },
  { id: 5, name: "评论垃圾检测", cron: "*/30 * * * *", last: "2026-03-26 10:30", next: "2026-03-26 11:00", status: "idle" },
]);
const editing = ref<Job | null>(null);
function openNew() { editing.value = { id: 0, name: "", cron: "0 * * * *", status: "idle" }; }
async function run(j: Job) { try { j.status = "running"; await apiPost(`/api/admin/scheduler/${j.id}/run`); alert("已触发"); } catch (e: any) { alert(e?.message || "触发失败"); } finally { setTimeout(() => (j.status = j.lastError ? "error" : "idle"), 1500); } }
function toggle(j: Job) { j.status = j.status === "idle" ? "running" : "idle"; }
function del(j: Job) { if (!confirm(`删除任务 ${j.name}?`)) return; jobs.value = jobs.value.filter(x => x.id !== j.id); }
</script>

<template>
  <div class="space-y-lg">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-neutral-text-primary">定时任务</h1>
      <button @click="openNew" class="px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 inline-flex items-center gap-1 shadow-sm">
        <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新建任务
      </button>
    </header>

    <section v-if="editing" class="bg-neutral-bg-container border border-primary-500/40 rounded-2xl p-lg shadow-lg ring-4 ring-primary-500/10 max-w-2xl">
      <h3 class="font-semibold mb-sm text-neutral-text-primary">{{ (editing as any).id ? '编辑' : '新建' }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm text-sm">
        <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">任务名</span>
          <input v-model="(editing as any).name" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
        <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Cron（5 字段）</span>
          <input v-model="(editing as any).cron" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono"/></label>
        <label class="self-end">
          <span class="text-xs text-neutral-text-tertiary block mb-1">常用：</span>
          <div class="flex flex-wrap gap-xs">
            <button v-for="c in ['* * * * *','0 * * * *','0 0 * * *','30 2 * * 0','0 9-18 * * 1-5']" :key="c"
              @click="(editing as any).cron = c"
              class="px-2 py-1 text-xs rounded bg-neutral-fill-hover hover:bg-primary-500 hover:text-white transition-colors font-mono">{{ c }}</button>
          </div>
        </label>
      </div>
      <div class="mt-md flex justify-end gap-xs">
        <button @click="editing = null" class="px-4 h-9 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm">取消</button>
        <button @click="jobs.value.push(editing as Job); editing = null" class="px-4 h-9 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400">保存</button>
      </div>
    </section>

    <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-neutral-fill-hover text-xs text-neutral-text-tertiary uppercase">
          <tr>
            <th class="px-4 py-3 text-left font-medium">任务</th>
            <th class="px-4 py-3 text-left font-medium hidden sm:table-cell">Cron</th>
            <th class="px-4 py-3 text-left font-medium hidden md:table-cell">上次运行</th>
            <th class="px-4 py-3 text-left font-medium hidden md:table-cell">下次运行</th>
            <th class="px-4 py-3 text-left font-medium">状态</th>
            <th class="px-4 py-3 text-right font-medium w-48">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-border-secondary">
          <tr v-for="j in jobs" :key="j.id" class="hover:bg-neutral-fill-hover/40">
            <td class="px-4 py-3">
              <p class="font-medium text-neutral-text-primary">{{ j.name }}</p>
              <p v-if="j.lastError" class="mt-xs text-[11px] text-danger-500">⚠ {{ j.lastError }}</p>
              <p v-if="j.count" class="mt-xs text-[11px] text-neutral-text-quaternary">累计执行 {{ j.count }} 次</p>
            </td>
            <td class="px-4 py-3 hidden sm:table-cell"><code class="font-mono text-xs px-2 py-1 rounded bg-neutral-fill-hover text-primary-500">{{ j.cron }}</code></td>
            <td class="px-4 py-3 text-xs text-neutral-text-secondary hidden md:table-cell tabular-nums">{{ j.last || '—' }}</td>
            <td class="px-4 py-3 text-xs text-neutral-text-secondary hidden md:table-cell tabular-nums">{{ j.next || '—' }}</td>
            <td class="px-4 py-3">
              <span class="text-[10px] px-2 py-0.5 rounded font-semibold"
                :class="j.status === 'running' ? 'bg-primary-500/10 text-primary-500' : j.status === 'error' ? 'bg-danger-500/10 text-danger-500' : 'bg-neutral-fill-hover text-neutral-text-tertiary'">
                {{ j.status === 'running' ? '运行中' : j.status === 'error' ? '出错' : '待机' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right text-xs whitespace-nowrap">
              <button @click="run(j)" class="text-success-500 hover:text-success-400 mr-xs inline-flex items-center gap-0.5">
                <Icon name="material-symbols:play-arrow-rounded" class="w-3.5 h-3.5"/>立即运行
              </button>
              <button @click="toggle(j)" class="text-primary-500 hover:text-primary-400 mr-xs inline-flex items-center gap-0.5">
                <Icon name="material-symbols:power-settings-new-rounded" class="w-3.5 h-3.5"/>启用
              </button>
              <button @click="del(j)" class="text-danger-500 hover:text-danger-400 inline-flex items-center gap-0.5">
                <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5"/>删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
