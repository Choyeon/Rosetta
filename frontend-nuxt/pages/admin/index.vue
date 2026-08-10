<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "仪表盘 - Rosetta 管理后台" });

interface Kpi { label: string; value: string | number; delta: string; up: boolean; icon: string; color: string }
const kpis: Kpi[] = [
  { label: "总文章", value: 0, delta: "+0%", up: true, icon: "material-symbols:article-rounded", color: "from-primary-500 to-nebula-blue" },
  { label: "今日访问", value: 0, delta: "+0%", up: true, icon: "material-symbols:visibility-rounded", color: "from-rosetta-gold to-warning-500" },
  { label: "分类/标签", value: "0 / 0", delta: "—", up: true, icon: "material-symbols:folder-supervised-rounded", color: "from-info-500 to-primary-500" },
  { label: "待审核评论", value: 0, delta: "—", up: false, icon: "material-symbols:forum-rounded", color: "from-success-500 to-info-500" },
];

// 真实数据：/api/stats/summary
const { data } = await useFetch<any>("/api/stats/summary", {
  default: () => ({ posts: 0, pages: 0, categories: 0, tags: 0, users: 0, uploads: 0, visitsToday: 0, commentsPending: 0 }),
  lazy: true,
  server: false,
});
watch(data, (d) => {
  if (!d) return;
  kpis[0].value = d.posts || 0;
  kpis[1].value = d.visitsToday || 0;
  kpis[2].value = `${d.categories || 0} / ${d.tags || 0}`;
  kpis[3].value = d.commentsPending || 0;
}, { immediate: true });

const { data: recent } = await useFetch<any[]>("/api/posts", {
  query: { pageSize: 5, _timeout: 6000 },
  default: () => ({ items: [] }),
  lazy: true,
  server: false,
});
</script>

<template>
  <div class="space-y-xl">
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-md">
      <div>
        <h1 class="text-2xl font-bold text-neutral-text-primary inline-flex items-center gap-xs">
          <Icon name="material-symbols:space-dashboard-rounded" class="w-6 h-6 text-primary-500"/>控制台
        </h1>
        <p class="text-sm text-neutral-text-tertiary mt-xs">今日概览 · {{ new Date().toLocaleDateString("zh-CN", { weekday: "long" }) }}</p>
      </div>
      <div class="flex items-center gap-xs flex-wrap">
        <NuxtLink to="/admin/posts/new" class="px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 inline-flex items-center gap-1.5 shadow-sm">
          <Icon name="material-symbols:add-rounded" class="w-4 h-4"/>新建文章
        </NuxtLink>
        <NuxtLink to="/admin/media" class="px-4 h-10 rounded-lg bg-neutral-fill-hover text-neutral-text-primary text-sm font-medium hover:bg-neutral-fill-active inline-flex items-center gap-1.5">
          <Icon name="material-symbols:cloud-upload-rounded" class="w-4 h-4"/>上传媒体
        </NuxtLink>
      </div>
    </header>

    <!-- KPI cards -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-md">
      <div v-for="k in kpis" :key="k.label" class="bg-neutral-bg-container rounded-2xl p-lg border border-neutral-border-secondary shadow-sm relative overflow-hidden group hover:-translate-y-0.5 hover:shadow-md transition-all">
        <div class="absolute -top-8 -right-8 w-28 h-28 rounded-full opacity-20 bg-gradient-to-br" :class="k.color" />
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs text-neutral-text-tertiary">{{ k.label }}</p>
            <p class="mt-xs text-3xl font-bold tabular-nums text-neutral-text-primary">{{ k.value }}</p>
          </div>
          <div class="w-11 h-11 rounded-xl flex items-center justify-center bg-gradient-to-br text-white shadow-sm" :class="k.color">
            <Icon :name="k.icon" class="w-6 h-6"/>
          </div>
        </div>
        <p class="mt-sm text-xs" :class="k.up ? 'text-success-500' : 'text-danger-500'">↑ 周同比 {{ k.delta }}</p>
      </div>
    </section>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-lg">
      <!-- Activity chart placeholder -->
      <section class="lg:col-span-2 bg-neutral-bg-container rounded-2xl p-lg border border-neutral-border-secondary shadow-sm">
        <header class="flex items-center justify-between mb-md">
          <h2 class="font-semibold text-neutral-text-primary">最近 14 天访问</h2>
          <div class="flex items-center gap-xs text-xs text-neutral-text-tertiary">
            <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-primary-500"/>UV</span>
            <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-rosetta-gold"/>PV</span>
          </div>
        </header>
        <div class="h-56 flex items-end gap-2 [&>*]:rounded-t-md [&>*]:transition-all [&>*]:hover:opacity-80">
          <div v-for="(h,i) in [20,35,60,45,70,85,55,90,65,80,75,50,40,62]" :key="i"
            class="flex-1 bg-gradient-to-t from-primary-500/60 to-primary-500" :style="{ height: h + '%' }"
            :title="`${new Date(Date.now()-(13-i)*864e5).toLocaleDateString()} UV`"/>
        </div>
      </section>

      <!-- Quick actions -->
      <section class="bg-neutral-bg-container rounded-2xl p-lg border border-neutral-border-secondary shadow-sm space-y-sm">
        <h2 class="font-semibold text-neutral-text-primary mb-xs">快捷操作</h2>
        <NuxtLink v-for="q in [
          { to: '/admin/posts/new', icon: 'material-symbols:edit-note-rounded', label: '新建文章', desc: 'Markdown 编辑器' },
          { to: '/admin/media', icon: 'material-symbols:perm-media-album-rounded', label: '媒体库', desc: '上传 / 管理图片' },
          { to: '/admin/categories', icon: 'material-symbols:category-rounded', label: '分类/标签', desc: '维护内容结构' },
          { to: '/admin/settings', icon: 'material-symbols:tune-rounded', label: '站点设置', desc: 'SEO · 功能 · 主题' },
        ]" :key="q.to" :to="q.to" class="flex items-center gap-sm p-xs rounded-xl hover:bg-neutral-fill-hover transition-all">
          <span class="w-10 h-10 rounded-lg bg-primary-500/10 text-primary-500 flex items-center justify-center"><Icon :name="q.icon" class="w-5 h-5"/></span>
          <span class="min-w-0 flex-1">
            <p class="text-sm font-medium text-neutral-text-primary">{{ q.label }}</p>
            <p class="text-xs text-neutral-text-tertiary truncate">{{ q.desc }}</p>
          </span>
          <Icon name="material-symbols:chevron-right-rounded" class="w-4 h-4 text-neutral-text-quaternary"/>
        </NuxtLink>
      </section>
    </div>

    <!-- Recent posts + Activity log -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-lg">
      <section class="lg:col-span-2 bg-neutral-bg-container rounded-2xl p-lg border border-neutral-border-secondary shadow-sm">
        <header class="flex items-center justify-between mb-md">
          <h2 class="font-semibold text-neutral-text-primary">最近文章</h2>
          <NuxtLink to="/admin/posts" class="text-xs text-primary-500 hover:underline">全部</NuxtLink>
        </header>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-neutral-text-tertiary">
              <th class="py-2 font-medium">标题</th>
              <th class="py-2 font-medium hidden sm:table-cell">分类</th>
              <th class="py-2 font-medium hidden md:table-cell">状态</th>
              <th class="py-2 font-medium">发布时间</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-border-secondary">
            <tr v-for="p in ((recent as any)?.items || [])" :key="p.id || p.slug" class="hover:bg-neutral-fill-hover/50">
              <td class="py-2 font-medium text-neutral-text-primary">
                <NuxtLink :to="`/admin/posts/${p.id || 1}`" class="hover:text-primary-500">{{ p.title }}</NuxtLink>
              </td>
              <td class="py-2 hidden sm:table-cell text-xs text-neutral-text-secondary">{{ p.category || '—' }}</td>
              <td class="py-2 hidden md:table-cell">
                <span v-if="p.published" class="px-2 py-0.5 rounded text-[10px] font-semibold bg-success-500/10 text-success-600">已发布</span>
                <span v-else class="px-2 py-0.5 rounded text-[10px] font-semibold bg-neutral-fill-hover text-neutral-text-tertiary">草稿</span>
              </td>
              <td class="py-2 text-xs text-neutral-text-tertiary tabular-nums">{{ p.published ? new Date(p.published).toLocaleDateString() : '—' }}</td>
            </tr>
            <tr v-if="(recent as any)?.items?.length === 0"><td colspan="4" class="py-8 text-center text-neutral-text-tertiary text-sm">暂无文章</td></tr>
          </tbody>
        </table>
      </section>

      <section class="bg-neutral-bg-container rounded-2xl p-lg border border-neutral-border-secondary shadow-sm">
        <h2 class="font-semibold text-neutral-text-primary mb-md">活动日志</h2>
        <ol class="relative border-l border-neutral-border-secondary pl-md space-y-sm">
          <li v-for="(a,i) in [
            { t:'10:24', ttl:'更新文章：Nuxt 4 迁移指南', lvl:'edit' },
            { t:'09:40', ttl:'上传新图片：hero-2026q2.webp', lvl:'media' },
            { t:'09:02', ttl:'登录后台（127.0.0.1）', lvl:'auth' },
            { t:'昨日', ttl:'发布文章：Astro 7 → Nuxt 4', lvl:'publish' },
            { t:'昨日', ttl:'修改站点设置：新增标签页', lvl:'settings' },
          ]" :key="i" class="relative">
            <span class="absolute -left-[19px] top-1.5 w-2.5 h-2.5 rounded-full"
              :class="{ 'bg-primary-500': a.lvl==='edit', 'bg-success-500': a.lvl==='publish', 'bg-info-500': a.lvl==='media', 'bg-rosetta-gold': a.lvl==='auth', 'bg-neutral-text-quaternary': a.lvl==='settings' }"/>
            <p class="text-sm text-neutral-text-primary">{{ a.ttl }}</p>
            <p class="text-xs text-neutral-text-quaternary tabular-nums">{{ a.t }}</p>
          </li>
        </ol>
      </section>
    </div>
  </div>
</template>
