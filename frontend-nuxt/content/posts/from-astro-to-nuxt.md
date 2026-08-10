---
title: 从 Astro 7 迁移到 Nuxt 4：完整迁移笔记
published: 2026-05-20
updated: 2026-05-20
pinned: true
draft: false
description: 记录将 Rosetta 从 Astro 7 完整迁移到 Nuxt 4.5.2 的 9 阶段计划、设计体系转换、Content Collections 替换、管理后台迁移与关键决策点。
image: "./images/rosetta1.avif"
tags: ["Nuxt 4", "Astro", "迁移笔记", "Vue 3", "Tailwind v4", "工程化"]
category: "迁移笔记"
lang: zh-CN
author: Choyu Choyeon
comment: true
slug: from-astro-to-nuxt
---

# 从 Astro 7 迁移到 Nuxt 4：Rosetta 完整迁移笔记

> 该文为迁移期种子内容，说明 Astro→Nuxt 替换路径；正式上线后将被真实文章覆盖。

## 背景与目标

Rosetta 博客最初基于 Astro 7 构建，享有优秀的首屏静态性能、内容优先 DX。随着内容页外的**管理后台、登录态、搜索、动态时间线**等交互增多，Vue 生态带来的 **SSR 全链路 + Pinia 状态 + Nitro API** 能让前后端交互边界更统一，避免「Astro + Svelte 组件岛 + 手写 fetch 客户端」三种框架并存的心智负担。

迁移后目标：
1. **路由完全兼容**：保持 `/posts/[...slug]`、`/tags/`、`/categories/`、`/archive`、`/friends`、`/guestbook`、`/sponsor`、`/anime`、`/bangumi`、`/dynamic`、`/gallery` 等 URL 不变
2. **视觉 1:1**：tokens/颜色/字体/间距/动画曲线与原 Ant Design 风格 100% 对齐
3. **内容无缝复用**：Astro Content Collections 的 frontmatter schema（`title/published/draft/tags/category/slug/image/comment/password/...`）全部在 Nuxt Content v3 下生效
4. **管理后台等价**：admin/ 目录下 20+ 页面迁移到 Vue 3 + @nuxt/ui + Pinia RBAC
5. **SSR + ISR**：热点页面 ISR（增量静态重生成）+ 敏感路由 SSR 私有缓存

## 9 阶段迁移计划

1. ✅ 阶段 1：审计 Astro 代码结构 → 产出清单
2. ✅ 阶段 2：骨架初始化（package.json/nuxt.config.ts/layouts/stores/composables/.env）
3. ✅ 阶段 3：设计体系 + 公共层（Logo/Header/Footer/侧栏/模态/PopupManager）
4. 🔄 阶段 4：内容层（Content Collections → Nuxt Content v3）
5. ⏳ 阶段 5：路由 + 页面
6. ⏳ 阶段 6：管理后台
7. ⏳ 阶段 7：API 代理 + Auth
8. ⏳ 阶段 8：验证 + 切换
9. ⏳ 阶段 9：提交（原 frontend/ 标记 legacy-astro 暂不删除）

## 设计体系转换

Astro 项目使用 `src/styles/tokens-antd.json` + `tokens-antd.css` 定义设计令牌。迁移到 Nuxt 4 + Tailwind v4 后，使用：

```css
/* assets/css/tokens.css (main.css @import) */
@theme {
  --color-primary-500: #1677ff;
  --color-success-500: #52c41a;
  --color-warning-500: #faad14;
  --color-danger-500:  #f5222d;
  --color-info-500:    #13c2c2;
  --color-nebula-blue: #2f54eb;
  --color-rosetta-gold: #f5c16c;
  /* 阴影/圆角/间距/动画 ... */
}
```

深浅两套主题通过 `<html data-theme="one-dark-pro" />` 属性切换，对应 [data-theme="one-dark-pro"] 下所有 CSS 变量覆盖，保证主题切换瞬间无白屏（FOUC 通过 `app.vue` 顶部内联脚本 + localStorage 先于 CSSOM 读取解决）。

## 内容层替换

| Astro | Nuxt 4 | 说明 |
|---|---|---|
| `src/content/posts/*.md` | `content/posts/*.md` | 路由前缀 `/posts/` 保持一致 |
| `src/content/spec/*.md`  | `content/spec/*.md`  | 独立页面内容层，`/pages/about.vue` 等页面可选择**使用或覆盖**该层 |
| `src/content/dynamic/*.md` | `content/dynamic/*.md` | 动态时间线（短内容） |
| `src/content.config.ts` Zod schema | Nuxt Content 的 frontmatter 约定 | 字段名 1:1：`title/published/updated/draft/description/image/tags/category/lang/pinned/author/sourceLink/licenseName/licenseUrl/comment/password/passwordHint/slug` |
| Astro remark/rehype 插件（wiki-link/mermaid/plantuml/excerpt） | Nuxt Content `markdown.remarkPlugins[] / rehypePlugins[]` | 阶段 8 引入 |
| Shiki `one-light` / `one-dark-pro` | content.highlight.theme { default, "one-dark-pro" } | 多主题已就位 |

## API 代理 + Auth

```ts
// nitro.routeRules + devProxy
"/api/**":   { proxy: "http://127.0.0.1:8000/api/**" }
"/media/**": { proxy: "http://127.0.0.1:8000/media/**" }
```

Token 双份存储：
- `localStorage.rosetta_token` → 客户端读取、发送 `Authorization: Bearer`
- `Cookie: rosetta_token` → SSR 阶段通过 `useCookie` 读取 → 注入到后端的请求头，SSR 渲染出已登录视图

RBAC 使用 `stores/auth.ts` 的 `hasRole() / hasPerm()`：super_admin / admin / editor / author / contributor / guest。

## 小结

迁移的关键成功因素：
1. **先搭骨架再填肉**：配置 + 设计令牌 + Layout 先行，避免页面迁移时无容器
2. **schema 1:1**：内容层 frontmatter 不变，降低数据迁移风险
3. **Token 双份**：localStorage + Cookie，保证 SSR/CSR 鉴权都畅通
4. **每阶段 commit**：按规则每阶段 push 到 GitHub，保持 git log 可回溯

下一步：进入阶段 5 — 路由与页面迁移（首页/列表/文章详情/tags/categories/archive/search/友链/关于/OOBE/404）。
