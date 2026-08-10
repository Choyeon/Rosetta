<template>
  <!-- 首页占位（阶段 5 会完整迁移 PostList + 搜索 + 分类条） -->
  <div class="space-y-2xl">
    <!-- Hero 区 -->
    <section
      class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary-500 via-nebula-blue-75/80 to-rosetta-gold-dark shadow-lg p-2xl md:p-3xl text-white"
    >
      <div
        class="pointer-events-none absolute inset-0 opacity-20"
        aria-hidden
        style="background-image: radial-gradient(circle at 20% 20%, #fff 1px, transparent 1px), radial-gradient(circle at 80% 80%, #fff 1px, transparent 1px); background-size: 24px 24px;"
      />
      <div class="relative max-w-3xl">
        <p class="text-sm font-medium uppercase tracking-[0.24em] text-white/80 mb-sm">
          Rosetta — Lightweight Blog System
        </p>
        <h1 class="text-[clamp(2rem,4vw,3rem)] font-bold leading-[1.15] mb-md">
          以<span class="text-rosetta-gold">内容</span>与
          <span class="text-rosetta-gold">体验</span>为核心的
          <br class="hidden md:block" />
          现代化博客引擎
        </h1>
        <p class="text-white/90 max-w-2xl leading-relaxed text-[15px]">
          正在从 Astro 7 迁移到 Nuxt 4 最新版 — 保留全部文章、标签、分类、
          管理后台、Markdown 生态与交互特性，同时带来更流畅的 SSR、
          更清晰的组件边界与更强的类型安全。
        </p>
        <div class="mt-xl flex flex-wrap gap-xs">
          <NuxtLink
            to="/posts"
            class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-white text-primary-700 font-semibold shadow-sm hover:bg-neutral-bg-spot active:translate-y-px transition-all duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 ring-white"
          >
            <Icon name="material-symbols:menu-book-rounded" class="w-5 h-5" />
            浏览文章
          </NuxtLink>
          <NuxtLink
            to="/about"
            class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-white/10 backdrop-blur-sm hover:bg-white/15 text-white font-medium border border-white/20 transition-all duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 ring-white"
          >
            <Icon name="material-symbols:info-rounded" class="w-5 h-5" />
            关于项目
          </NuxtLink>
          <NuxtLink
            to="/admin"
            class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-rosetta-gold text-neutral-text-primary font-semibold shadow-sm hover:bg-rosetta-gold-dark hover:text-white transition-all duration-fast ease-out"
          >
            <Icon name="material-symbols:dashboard-customize-rounded" class="w-5 h-5" />
            进入后台
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- 迁移进度卡片 -->
    <section
      class="grid grid-cols-1 md:grid-cols-3 gap-lg"
      aria-label="迁移进度"
    >
      <ProgressCard
        title="已完成初始化"
        :percent="25"
        subtitle="阶段 2 · 项目骨架 / 依赖 / Nuxt 配置"
        :ok="['Nuxt 4.5.2 初始化','@nuxt/ui + Pinia + VueUse 就绪','Tailwind v4 设计 Tokens 同步','i18n/API/Auth 工具迁移中']"
        :pending="['Content Collections','路由与页面','管理后台 20+ 页','OOBE Wizard','搜索与评论集成']"
        class="md:col-span-1"
      />
      <ProgressCard
        title="功能等价迁移"
        :percent="0"
        subtitle="阶段 4 · 内容层与数据层"
        :ok="[]"
        :pending="['posts/spec/dynamic 内容库','64 篇真实测试文章','站点级配置映射','分类/标签/归档数据管线','图片优化与 Fuse 搜索']"
        class="md:col-span-1"
      />
      <ProgressCard
        title="集成验证"
        :percent="0"
        subtitle="阶段 8 · 启动、构建与回归"
        :ok="[]"
        :pending="['pnpm dev 全链路冒烟','pnpm build 产物可运行','前端/后端 API 契约 OK','替换原 frontend 路径','打包脚本同步更新']"
        class="md:col-span-1"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
const ProgressCard = defineComponent({
  name: "ProgressCard",
  props: {
    title: String,
    percent: Number,
    subtitle: String,
    ok: { type: Array as () => string[], default: () => [] },
    pending: { type: Array as () => string[], default: () => [] },
  },
  setup(props) {
    return () =>
      h(
        "section",
        {
          class:
            "bg-neutral-bg-container rounded-2xl p-xl border border-neutral-border-secondary shadow-sm flex flex-col gap-md",
        },
        [
          h("div", { class: "flex items-start justify-between gap-md" }, [
            h("div", {}, [
              h("h2", { class: "text-lg font-semibold text-neutral-text-primary" }, props.title),
              h(
                "p",
                { class: "text-xs text-neutral-text-tertiary mt-0.5" },
                props.subtitle || ""
              ),
            ]),
            h(
              "span",
              {
                class:
                  "shrink-0 text-sm font-semibold text-primary-500 bg-primary-50 px-2.5 py-1 rounded-md",
              },
              `${props.percent}%`
            ),
          ]),
          h(
            "div",
            {
              class:
                "h-2 w-full rounded-full overflow-hidden bg-neutral-fill-quaternary",
            },
            [
              h("div", {
                class: "h-full bg-gradient-to-r from-primary-500 to-rosetta-gold transition-all",
                style: { width: `${props.percent}%` },
              }),
            ]
          ),
          ...(props.ok?.length
            ? [
                h("ul", { class: "space-y-xs text-sm" }, [
                  ...props.ok.map((t) =>
                    h(
                      "li",
                      { class: "flex items-start gap-xs text-neutral-text-secondary" },
                      [
                        h(
                          "span",
                          { class: "mt-0.5 text-success-500" },
                          "✓"
                        ),
                        t,
                      ]
                    )
                  ),
                ]),
              ]
            : []),
          ...(props.pending?.length
            ? [
                h("ul", { class: "space-y-xs text-sm" }, [
                  ...props.pending.map((t) =>
                    h(
                      "li",
                      { class: "flex items-start gap-xs text-neutral-text-tertiary" },
                      [
                        h(
                          "span",
                          { class: "mt-0.5 text-neutral-text-quaternary" },
                          "○"
                        ),
                        t,
                      ]
                    )
                  ),
                ]),
              ]
            : []),
        ]
      );
  },
});
</script>
