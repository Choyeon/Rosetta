<script lang="ts">
import {
	createPost,
	type Post,
	type PostCreate,
	type PostUpdate,
	updatePost,
} from "@api/blog";
import { createEventDispatcher, onDestroy, onMount, tick } from "svelte";
import CategorySelect, { type CategoryOption } from "./CategorySelect.svelte";
import CoverPicker from "./CoverPicker.svelte";
import MarkdownEditor from "./MarkdownEditor.svelte";
import TagChipsInput from "./TagChipsInput.svelte";

// ======== Props ========
export let isNew = true;
/** getPostForEdit 返回的数据（可能 title/content 为 dict 多语言结构，也可能为 string，需兼容） */
export let initialData: any = null;
export let categories: CategoryOption[] = [];
/** 用于标签建议的现有标签名列表 */
export let existingTags: string[] = [];

// ======== SSR 初始数据注入 (Astro client:only 模式下从 window 读取) ========
type SsrInitialState = {
	isNew?: boolean;
	/** postId 存在但 post 为 null → 客户端自行按 postId 拉详情 */
	postId?: number;
	post?: any;
	categories?: CategoryOption[];
	existingTags?: string[];
};
function readSsrInitialState(): SsrInitialState | null {
	try {
		if (typeof window === "undefined") return null;
		// 从 <script type="application/json" id="rosetta-editor-initial"> 读取
		const el = document.getElementById(
			"rosetta-editor-initial",
		) as HTMLScriptElement | null;
		if (el?.textContent) {
			const parsed = JSON.parse(el.textContent);
			if (parsed && typeof parsed === "object")
				return parsed as SsrInitialState;
		}
		// 兼容老的 window 挂法
		const g = (globalThis as any).__ROSETTA_EDITOR_INITIAL__ as
			| SsrInitialState
			| undefined;
		if (g && typeof g === "object") return g;
	} catch {
		/* ignore */
	}
	return null;
}

async function ensureBootstrapData() {
	const ssr = readSsrInitialState();
	if (ssr) {
		if (typeof ssr.isNew === "boolean") isNew = ssr.isNew;
		if (
			Array.isArray(ssr.categories) &&
			ssr.categories.length &&
			!categories.length
		) {
			categories = ssr.categories;
		}
		if (Array.isArray(ssr.existingTags) && !existingTags.length) {
			existingTags = ssr.existingTags;
		}
		if (ssr.post && !initialData) initialData = ssr.post;
	}

	// === 拉取 categories + existingTags（如果 SSR 没注入） ===
	let mod: typeof import("@api/blog") | null = null;
	const getApiMod = async () => {
		if (!mod) mod = await import("@api/blog");
		return mod;
	};
	try {
		if (!categories.length || !existingTags.length) {
			const m = await getApiMod();
			if (!categories.length) {
				const cats = await m.getCategories?.();
				if (Array.isArray(cats)) categories = cats;
			}
			if (!existingTags.length) {
				const tags = await m.getTags?.();
				if (Array.isArray(tags)) {
					existingTags = tags
						.map((t: any) => (typeof t === "string" ? t : t?.name))
						.filter(Boolean) as string[];
				}
			}
		}
	} catch (e) {
		console.warn("[PostEditorForm] lazy fetch meta failed:", e);
	}

	// === 拉取文章详情：SSR 只给了 postId（无 post payload）→ 客户端按 id 拉 ===
	if (!isNew && !initialData && ssr?.postId && Number.isFinite(ssr.postId)) {
		try {
			const m = await getApiMod();
			const loaded = await m.getPostById?.(ssr.postId);
			if (loaded) {
				initialData = loaded;
				postId = Number((loaded as any).id ?? ssr.postId);
			}
		} catch (e) {
			console.warn("[PostEditorForm] lazy fetch post failed:", e);
		}
	}

	applyInitialData();
	// 确保响应式刷新 tick
	await tick();
}

const dispatch = createEventDispatcher<{
	saved: { id: number; status: string };
	cancel: undefined;
}>();

// ======== i18n helpers (兼容后端 多语言 dict / string 两种输入) ========
type I18nDict = Record<string, string>;
function i18nWrap(value: string): I18nDict {
	return { zh_CN: value || "", zh: value || "" };
}
function i18nUnwrap(v: any, fallback = ""): string {
	if (typeof v === "string") return v;
	if (v && typeof v === "object") {
		return v.zh_CN ?? v.zh ?? v.en ?? Object.values(v)[0] ?? fallback;
	}
	return fallback;
}

// ======== Toast ========
type ToastType = "success" | "error" | "info";
let toastHost: HTMLDivElement | null = null;
function showToast(message: string, type: ToastType = "info") {
	if (!toastHost) return;
	const toast = document.createElement("div");
	toast.className = `pef-toast pef-toast-${type}`;
	const iconMap: Record<ToastType, string> = {
		success:
			'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
		error:
			'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
		info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
	};
	toast.innerHTML = `${iconMap[type] || iconMap.info}<span>${message}</span>`;
	toastHost.appendChild(toast);
	setTimeout(() => {
		toast.classList.add("pef-toast-leave");
		setTimeout(() => toast.remove(), 300);
	}, 3000);
}

// ======== Form State ========
let postId: number | null = initialData?.id ?? null;
let title = "";
let slug = "";
let excerpt = "";
let content = "";
let mdContent = ""; // last known editor content (from event)
let cover_image: string | null = null;
let status: "draft" | "published" | "scheduled" = "draft";
let scheduled_at = ""; // <input type="datetime-local"> 格式
let visibility: "public" | "password" | "private" = "public";
let is_pinned = false;
let is_featured = false;
let allow_comments = true;
let password = "";
let categoryId: number | null = null;
let tagNames: string[] = [];
let encryptionEnabled = false;
let encryptionData: { salt?: string; verifier?: string; algorithm?: string } =
	{};

let saving = false;
let wordCount = 0;
let readingTime = 0;

// ======== MarkdownEditor 实例引用（用于取实时内容） ========
let mdEditorRef: any = null;
function setMdRef(el: any) {
	if (!el) return;
	// client:only svelte 会把组件实例挂到 __svelte_component / _svelte_component
	mdEditorRef =
		(el as any).__svelte_component ?? (el as any)._svelte_component ?? null;
}
function syncEditorContentNow() {
	if (!mdEditorRef) return mdContent;
	try {
		const fn = mdEditorRef.getMarkdown;
		if (typeof fn === "function") {
			const v = fn.call(mdEditorRef);
			if (typeof v === "string") mdContent = v;
		} else {
			const v = mdEditorRef.value ?? mdEditorRef.content ?? undefined;
			if (typeof v === "string") mdContent = v;
		}
	} catch (e) {
		console.warn("[PostEditorForm] getMarkdown failed:", e);
	}
	return mdContent;
}

// ======== 初始化: 用 initialData 填充表单 ========
function applyInitialData() {
	if (!initialData) return;
	postId = Number(initialData.id) || null;
	title = i18nUnwrap(initialData.title);
	slug = initialData.slug || "";
	excerpt = i18nUnwrap(
		initialData.excerpt ?? initialData.summary ?? initialData.subtitle,
	);
	content = i18nUnwrap(initialData.content);
	mdContent = content;
	cover_image = initialData.cover_image || null;
	status =
		(initialData.status as "draft" | "published" | "scheduled") || "draft";
	if (initialData.scheduled_at) {
		const dt = new Date(initialData.scheduled_at);
		if (!Number.isNaN(dt.getTime())) {
			const pad = (n: number) => String(n).padStart(2, "0");
			scheduled_at = `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
		}
	}
	visibility =
		(initialData.visibility as "public" | "password" | "private") || "public";
	is_pinned = !!initialData.is_pinned;
	is_featured = !!initialData.is_featured;
	allow_comments = initialData.allow_comments !== false;
	password = initialData.password || "";
	if (initialData.category?.id) {
		categoryId = Number(initialData.category.id);
	} else if (typeof initialData.category_id === "number") {
		categoryId = initialData.category_id;
	}
	const tags: any[] = initialData.tags || [];
	tagNames = tags
		.map((t) => i18nUnwrap(typeof t === "object" ? t.name : t))
		.filter(Boolean);
	encryptionEnabled = !!initialData.encryption_enabled;
	encryptionData = {
		salt: initialData.encryption_salt ?? undefined,
		verifier: initialData.encryption_verifier ?? undefined,
		algorithm: initialData.encryption_algorithm ?? undefined,
	};
	updateStats(mdContent + title + excerpt);
}

onMount(() => {
	ensureBootstrapData();
});

// ======== MarkdownEditor 事件回调 ========
function onMdValueChange(e: any) {
	const v: string | undefined = e?.detail?.value ?? e?.value ?? undefined;
	if (typeof v === "string") {
		mdContent = v;
		content = v;
		updateStats(v + title + excerpt);
	}
}
function onEncryptionChange(e: any) {
	const d = e?.detail ?? e ?? {};
	encryptionEnabled = !!d.enabled;
	encryptionData = d.data ?? d.encryptionData ?? {};
}
function onStatusChange(e: any) {
	const v = e?.detail ?? e;
	if (typeof v === "string") status = v as any;
}
function onScheduledChange(e: any) {
	const d = e?.detail ?? e ?? {};
	if (d.iso) scheduled_at = toLocalInput(d.iso);
	if (d.enable && status !== "scheduled") status = "scheduled";
}

function toLocalInput(iso: string) {
	try {
		const dt = new Date(iso);
		if (Number.isNaN(dt.getTime())) return iso;
		const pad = (n: number) => String(n).padStart(2, "0");
		return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
	} catch {
		return iso;
	}
}

// ======== 字数/阅读时间 ========
function updateStats(allText: string) {
	const t = allText || "";
	// 中文按字符计数，英文按单词
	const zh = (t.match(/[\u4e00-\u9fa5]/g) || []).length;
	const enWords = (t.match(/[A-Za-z]+/g) || []).length;
	wordCount = zh + enWords;
	// 阅读: 中文 500/min，英文 200/min，取较大估算
	const zhMin = zh / 500;
	const enMin = enWords / 220;
	readingTime = Math.max(1, Math.ceil(zhMin + enMin));
}
$: updateStats((mdContent || content) + title + excerpt);

// ======== 侧栏状态联动 ========
$: if (scheduled_at && status !== "scheduled") {
	// 用户手动选了时间 → 自动变 scheduled
	status = "scheduled";
}
$: if (visibility !== "password" && password) {
	// 选了非密码可见性但填了密码 → 清空密码（避免歧义）
	// 不强制清空，用户可能只是在切换，保留原值即可
}

// ======== 保存/发布 ========
function buildPayload(actionStatus: "draft" | "published"): any {
	const latestContent = syncEditorContentNow() || content || "";
	const finalStatus: "draft" | "published" | "scheduled" =
		actionStatus === "published" && !scheduled_at
			? "published"
			: scheduled_at
				? "scheduled"
				: actionStatus;

	const cat =
		categoryId != null && Number.isFinite(categoryId)
			? Number(categoryId)
			: undefined;

	const data: any = {
		title: i18nWrap(title),
		content: i18nWrap(latestContent),
		excerpt: i18nWrap(excerpt),
		summary: i18nWrap(excerpt),
		status: finalStatus,
		slug: slug || undefined,
		category_id: cat ?? null,
		tags: tagNames.length ? tagNames : undefined,
		tag_names: tagNames.length ? tagNames : undefined,
		cover_image: cover_image || undefined,
		is_pinned,
		is_featured,
		allow_comments,
		// ===== 关键修复: visibility 必须显式入 payload =====
		visibility,
		password: visibility === "password" ? password || undefined : undefined,
	};

	if (scheduled_at) {
		const dt = new Date(scheduled_at);
		if (!Number.isNaN(dt.getTime())) data.scheduled_at = dt.toISOString();
	}
	if (encryptionEnabled) {
		data.encryption_enabled = true;
		data.encryption_salt = encryptionData?.salt ?? null;
		data.encryption_verifier = encryptionData?.verifier ?? null;
		data.encryption_algorithm = encryptionData?.algorithm ?? "AES-256-GCM";
	}
	return data;
}

async function savePost(actionStatus: "draft" | "published") {
	if (saving) return;
	if (!title.trim()) {
		showToast("请输入标题", "error");
		return;
	}
	if (visibility === "password" && !password) {
		showToast("可见性=密码时，请输入访问密码", "error");
		return;
	}
	const latest = syncEditorContentNow();
	if (!latest?.trim()) {
		showToast("请输入正文内容", "error");
		return;
	}

	saving = true;
	try {
		const payload = buildPayload(actionStatus);
		const result: any = isNew
			? await createPost(payload as PostCreate)
			: await updatePost(postId!, payload as PostUpdate);
		const savedId = Number(result?.id);
		showToast(
			actionStatus === "published" && payload.status === "published"
				? "文章已发布"
				: payload.status === "scheduled"
					? "已加入定时发布计划"
					: "草稿已保存",
			"success",
		);
		dispatch("saved", {
			id: savedId,
			status: payload.status,
		});
		if (savedId) {
			// 跳转到编辑页（让 new→edit，edit 保持不变）
			setTimeout(() => {
				window.location.href = `/admin/posts/${savedId}/`;
			}, 650);
		} else {
			setTimeout(() => {
				window.location.href = "/admin/posts/";
			}, 650);
		}
	} catch (e: any) {
		console.error("[savePost] error:", e);
		showToast(e?.message || (e as any)?.detail || "保存失败", "error");
	} finally {
		saving = false;
	}
}

function saveDraft() {
	savePost("draft");
}
function publish() {
	savePost("published");
}
function handleCancel() {
	dispatch("cancel");
	window.location.href = "/admin/posts/";
}
function handlePreview() {
	showToast("预览功能暂未启用", "info");
}

// ======== 导航离开提示 ========
let dirty = false;
$: if (title || content || tagNames.length || excerpt) dirty = true;
function onBeforeUnload(e: BeforeUnloadEvent) {
	if (!dirty || saving) return;
	e.preventDefault();
	e.returnValue = "";
}
onMount(() => {
	window.addEventListener("beforeunload", onBeforeUnload);
});
onDestroy(() => {
	window.removeEventListener("beforeunload", onBeforeUnload);
});
</script>

<div class="pef-root">
  <!-- ========= Page Header ========= -->
  <div class="pef-header">
    <div class="pef-header-left">
      <a href="/admin/posts/" class="pef-back-btn" aria-label="返回文章列表" on:click|preventDefault={handleCancel}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      </a>
      <nav class="pef-breadcrumb" aria-label="面包屑">
        <span class="pef-bc-item"><a href="/admin/">管理后台</a></span>
        <span class="pef-bc-sep">/</span>
        <span class="pef-bc-item"><a href="/admin/posts/">文章管理</a></span>
        <span class="pef-bc-sep">/</span>
        <span class="pef-bc-item active">{isNew ? "新建文章" : "编辑文章"}</span>
      </nav>
      <h1 class="pef-page-title">{isNew ? "新建文章" : "编辑文章"}</h1>
    </div>
    <div class="pef-header-right">
      <div class="pef-btn-group">
        <button class="pef-btn pef-btn-ghost" on:click={handleCancel} disabled={saving}>取消</button>
        <button class="pef-btn pef-btn-link" on:click={handlePreview} disabled={saving}>预览</button>
        <button class="pef-btn pef-btn-default" on:click={saveDraft} disabled={saving}>
          {#if saving}保存中…{:else}存草稿{/if}
        </button>
        <button class="pef-btn pef-btn-primary" on:click={publish} disabled={saving}>
          {#if saving}保存中…{:else}发布{/if}
        </button>
      </div>
    </div>
  </div>

  <!-- ========= Main Layout ========= -->
  <div class="pef-layout">
    <!-- ========= Main Column ========= -->
    <div class="pef-main">
      <div class="pef-card pef-main-card">
        <div class="pef-card-body">
          <!-- 标题 -->
          <div class="pef-field">
            <label class="pef-label pef-required" for="pef-title">标题</label>
            <div class="pef-control">
              <input
                id="pef-title"
                class="pef-input pef-input-title"
                type="text"
                bind:value={title}
                placeholder="请输入文章标题"
                maxlength={200}
              />
            </div>
          </div>

          <!-- Slug -->
          <div class="pef-field">
            <label class="pef-label" for="pef-slug">别名 Slug</label>
            <div class="pef-control">
              <input
                id="pef-slug"
                class="pef-input"
                type="text"
                bind:value={slug}
                placeholder="留空自动生成（建议英文、数字、短横）"
                pattern="[a-z0-9-]*"
              />
            </div>
          </div>

          <!-- 摘要 -->
          <div class="pef-field">
            <label class="pef-label" for="pef-excerpt">摘要</label>
            <div class="pef-control">
              <textarea
                id="pef-excerpt"
                class="pef-input pef-textarea"
                rows={4}
                bind:value={excerpt}
                placeholder="文章摘要（可选，用作列表页摘要、SEO description 备选）"
              />
            </div>
          </div>

          <!-- 编辑器 -->
          <div class="pef-field">
            <label class="pef-label pef-required">正文</label>
            <div class="pef-control">
              <div
                id="md-editor-form-host"
                use:setMdRef
                class="pef-md-editor"
                on:rosetta:md-change={onMdValueChange}
              >
                <MarkdownEditor
                  postId={postId ?? "new"}
                  language="zh"
                  value={content}
                  status={status}
                  scheduledAt={scheduled_at ? new Date(scheduled_at).toISOString() : ""}
                  onValueChange={onMdValueChange}
                  onEncryptionChange={onEncryptionChange}
                  onScheduledChange={onScheduledChange}
                  onStatusChange={onStatusChange}
                />
              </div>
            </div>
          </div>

          <!-- 底部按钮 -->
          <div class="pef-actions">
            <div class="pef-btn-group">
              <button class="pef-btn pef-btn-ghost" on:click={handleCancel} disabled={saving}>取消</button>
              <button class="pef-btn pef-btn-link" on:click={handlePreview} disabled={saving}>预览</button>
              <button class="pef-btn pef-btn-default" on:click={saveDraft} disabled={saving}>
                {#if saving}保存中…{:else}存草稿{/if}
              </button>
              <button class="pef-btn pef-btn-primary" on:click={publish} disabled={saving}>
                {#if saving}保存中…{:else}发布{/if}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========= Sidebar Column ========= -->
    <aside class="pef-sidebar">
      <!-- 发布设置 -->
      <section class="pef-card pef-side-card">
        <header class="pef-card-header">
          <span class="pef-card-title">发布设置</span>
        </header>
        <div class="pef-card-body">
          <div class="pef-field">
            <label class="pef-label" for="pef-status">状态</label>
            <div class="pef-control">
              <select id="pef-status" class="pef-select" bind:value={status}>
                <option value="draft">草稿</option>
                <option value="scheduled">定时发布</option>
                <option value="published">已发布</option>
              </select>
            </div>
          </div>

          <div class="pef-field">
            <label class="pef-label" for="pef-visibility">可见性</label>
            <div class="pef-control">
              <select id="pef-visibility" class="pef-select" bind:value={visibility}>
                <option value="public">公开</option>
                <option value="password">密码保护</option>
                <option value="private">私密（仅作者）</option>
              </select>
            </div>
          </div>

          <div class="pef-field">
            <label class="pef-label" for="pef-scheduled-at">发布时间</label>
            <div class="pef-control">
              <input
                id="pef-scheduled-at"
                class="pef-input"
                type="datetime-local"
                bind:value={scheduled_at}
              />
            </div>
          </div>

          <div class="pef-field pef-field-inline">
            <label class="pef-label">置顶</label>
            <div class="pef-control">
              <label class="pef-switch">
                <input type="checkbox" bind:checked={is_pinned} />
                <span class="pef-switch-slider" />
              </label>
            </div>
          </div>

          <div class="pef-field pef-field-inline">
            <label class="pef-label">允许评论</label>
            <div class="pef-control">
              <label class="pef-switch">
                <input type="checkbox" bind:checked={allow_comments} />
                <span class="pef-switch-slider" />
              </label>
            </div>
          </div>

          <div class="pef-field" class:pef-muted={visibility !== "password"}>
            <label class="pef-label" for="pef-password">访问密码</label>
            <div class="pef-control">
              <input
                id="pef-password"
                class="pef-input"
                type="text"
                bind:value={password}
                placeholder={visibility === "password" ? "请输入访问密码（4~100 字符）" : "仅在可见性=密码时生效"}
                maxlength={100}
              />
            </div>
          </div>

          <div class="pef-field pef-field-inline">
            <label class="pef-label">整文加密</label>
            <div class="pef-control">
              <label class="pef-switch">
                <input
                  type="checkbox"
                  bind:checked={encryptionEnabled}
                  disabled
                  aria-describedby="pef-enc-hint"
                />
                <span class="pef-switch-slider" />
              </label>
              <div class="pef-hint" id="pef-enc-hint">在编辑器工具栏「启用加密」设置密码</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 分类 & 标签 & 封面 -->
      <section class="pef-card pef-side-card">
        <header class="pef-card-header">
          <span class="pef-card-title">分类 · 标签 · 封面</span>
        </header>
        <div class="pef-card-body">
          <div class="pef-field">
            <label class="pef-label">分类</label>
            <div class="pef-control">
              <CategorySelect
                bind:categoryId
                categories={categories}
                allowClear={true}
              />
            </div>
          </div>

          <div class="pef-field">
            <label class="pef-label">标签</label>
            <div class="pef-control">
              <TagChipsInput
                bind:tags={tagNames}
                suggestions={existingTags}
                placeholder="输入标签后回车添加，逗号分隔"
              />
            </div>
          </div>

          <div class="pef-field">
            <label class="pef-label">封面图片</label>
            <div class="pef-control">
              <CoverPicker bind:coverUrl={cover_image} />
            </div>
          </div>

          <div class="pef-field pef-field-inline">
            <label class="pef-label">推荐文章</label>
            <div class="pef-control">
              <label class="pef-switch">
                <input type="checkbox" bind:checked={is_featured} />
                <span class="pef-switch-slider" />
              </label>
            </div>
          </div>
        </div>
      </section>

      <!-- 文章信息 -->
      <section class="pef-card pef-side-card">
        <header class="pef-card-header">
          <span class="pef-card-title">文章信息</span>
        </header>
        <div class="pef-card-body">
          <div class="pef-meta">
            <div class="pef-meta-item">
              <span class="pef-meta-label">字数</span>
              <span class="pef-meta-value">{wordCount} 字</span>
            </div>
            <div class="pef-meta-item">
              <span class="pef-meta-label">预计阅读</span>
              <span class="pef-meta-value">{readingTime} 分钟</span>
            </div>
            {#if postId}
              <div class="pef-meta-item">
                <span class="pef-meta-label">ID</span>
                <span class="pef-meta-value">#{postId}</span>
              </div>
            {/if}
          </div>
        </div>
      </section>
    </aside>
  </div>

  <!-- Toast host -->
  <div class="pef-toast-host" bind:this={toastHost} aria-live="polite" aria-atomic="true" />
</div>

<style lang="css">
  /* ========= Scoped Styles (局部) ========= */
  .pef-root {
    padding: 0 0 24px;
  }

  /* ---------- Header ---------- */
  .pef-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    padding: 16px 24px;
    background: var(--ant-bg-container, #fff);
    border-bottom: 1px solid var(--hairline, hsl(30 14% 90%));
    margin-bottom: 24px;
  }
  .pef-header-left {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  .pef-back-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    color: var(--walnut-700, hsl(24 10% 20%));
    transition: all 0.2s;
    cursor: pointer;
    text-decoration: none;
  }
  .pef-back-btn:hover {
    background: var(--walnut-50, hsl(40 30% 96%));
    color: var(--ochre-600, hsl(35 85% 50%));
  }
  .pef-breadcrumb {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: color-mix(in srgb, var(--walnut-600, hsl(24 10% 30%)) 80%, transparent);
  }
  .pef-bc-item a {
    color: inherit;
    text-decoration: none;
    transition: color 0.2s;
  }
  .pef-bc-item a:hover {
    color: var(--ochre-500, hsl(35 85% 50%));
  }
  .pef-bc-item.active {
    color: var(--walnut-800, hsl(24 10% 16%));
  }
  .pef-bc-sep {
    color: var(--walnut-300, hsl(24 10% 70%));
  }
  .pef-page-title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--walnut-900, hsl(24 10% 12%));
    line-height: 1.4;
  }
  .pef-header-right {
    display: flex;
    align-items: center;
  }

  /* ---------- Buttons ---------- */
  .pef-btn-group {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .pef-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 32px;
    padding: 4px 15px;
    font-size: 14px;
    line-height: 1.5715;
    border-radius: 6px;
    border: 1px solid transparent;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
    font-weight: 400;
    white-space: nowrap;
    user-select: none;
    text-decoration: none;
    box-sizing: border-box;
    font-family: inherit;
  }
  .pef-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .pef-btn-primary {
    background: var(--ochre-500, hsl(35 85% 50%));
    color: #fff;
    border-color: var(--ochre-500, hsl(35 85% 50%));
    box-shadow: 0 2px 0 color-mix(in srgb, var(--ochre-500, hsl(35 85% 50%)) 18%, transparent);
  }
  .pef-btn-primary:hover:not(:disabled) {
    background: var(--ochre-600, hsl(35 75% 42%));
    border-color: var(--ochre-600, hsl(35 75% 42%));
  }
  .pef-btn-default {
    background: var(--surface, #fff);
    color: var(--walnut-700, hsl(24 10% 20%));
    border-color: var(--walnut-200, hsl(30 14% 86%));
  }
  .pef-btn-default:hover:not(:disabled) {
    color: var(--ochre-500, hsl(35 85% 50%));
    border-color: var(--ochre-400, hsl(35 85% 60%));
  }
  .pef-btn-ghost {
    background: transparent;
    color: var(--walnut-700, hsl(24 10% 20%));
    border-color: transparent;
  }
  .pef-btn-ghost:hover:not(:disabled) {
    color: var(--ochre-500, hsl(35 85% 50%));
    background: color-mix(in srgb, var(--ochre-500, hsl(35 85% 50%)) 8%, transparent);
  }
  .pef-btn-link {
    background: transparent;
    color: var(--ochre-500, hsl(35 85% 50%));
    border-color: transparent;
    padding: 4px 0;
    height: auto;
  }
  .pef-btn-link:hover:not(:disabled) {
    color: var(--ochre-600, hsl(35 75% 42%));
  }

  /* ---------- Layout ---------- */
  .pef-layout {
    display: grid;
    grid-template-columns: 7fr 3fr;
    gap: 24px;
    padding: 0 24px;
    max-width: 1400px;
    margin: 0 auto;
  }
  @media (max-width: 1024px) {
    .pef-layout { grid-template-columns: 1fr; }
  }

  /* ---------- Card ---------- */
  .pef-card {
    background: var(--ant-bg-container, #fff);
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--hairline, hsl(30 14% 90%));
  }
  .pef-main-card {
    box-shadow: 0 1px 2px 0 rgba(0,0,0,0.03), 0 1px 6px -1px rgba(0,0,0,0.02), 0 2px 4px 0 rgba(0,0,0,0.02);
    border: none;
  }
  .pef-main-card > .pef-card-body {
    padding: 24px;
  }
  .pef-side-card {
    margin-bottom: 16px;
    background: var(--surface, #fff);
  }
  .pef-side-card:last-child { margin-bottom: 0; }
  .pef-card-header {
    padding: 14px 20px;
    border-bottom: 1px solid var(--hairline, hsl(30 14% 90%));
    min-height: 48px;
    display: flex;
    align-items: center;
  }
  .pef-card-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--walnut-800, hsl(24 10% 16%));
    line-height: 1.5;
  }
  .pef-card-body {
    padding: 20px;
  }

  /* ---------- Field ---------- */
  .pef-field {
    margin-bottom: 22px;
  }
  .pef-field:last-child { margin-bottom: 0; }
  .pef-field-inline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
  }
  .pef-field-inline .pef-label {
    margin-bottom: 0;
    width: auto;
  }
  .pef-field-inline .pef-control {
    width: auto;
  }
  .pef-field.pef-muted {
    opacity: 0.7;
  }
  .pef-label {
    display: block;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--walnut-800, hsl(24 10% 16%));
    line-height: 1.5715;
    margin-bottom: 8px;
  }
  .pef-label.pef-required::after {
    content: " *";
    color: hsl(6 65% 55%);
    font-family: SimSun, serif;
    margin-left: 2px;
  }
  .pef-control { position: relative; width: 100%; }

  .pef-input, .pef-select {
    width: 100%;
    height: 34px;
    padding: 5px 12px;
    font-size: 14px;
    line-height: 1.5715;
    color: var(--walnut-800, hsl(24 10% 16%));
    background: var(--input-bg, var(--card-bg, #fff));
    border: 1px solid var(--hairline, hsl(30 14% 86%));
    border-radius: 6px;
    transition: all 0.2s;
    outline: none;
    box-sizing: border-box;
    font-family: inherit;
  }
  .pef-input:hover, .pef-select:hover {
    border-color: var(--ochre-400, hsl(35 85% 60%));
  }
  .pef-input:focus, .pef-select:focus {
    border-color: var(--ochre-500, hsl(35 85% 50%));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--ochre-500, hsl(35 85% 50%)) 22%, transparent);
  }
  .pef-input::placeholder, .pef-textarea::placeholder {
    color: color-mix(in srgb, var(--walnut-500, hsl(24 10% 45%)) 70%, transparent);
  }
  .pef-input-title {
    height: 42px;
    font-size: 16.5px;
    font-weight: 500;
    padding: 7px 13px;
  }
  .pef-textarea {
    height: auto;
    min-height: 96px;
    resize: vertical;
    padding: 7px 12px;
    line-height: 1.6;
  }
  .pef-md-editor {
    width: 100%;
    min-height: 480px;
    border-radius: 8px;
    overflow: hidden;
  }

  /* ---------- Switch ---------- */
  .pef-switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 22px;
    cursor: pointer;
    vertical-align: middle;
  }
  .pef-switch input {
    opacity: 0;
    width: 0;
    height: 0;
    position: absolute;
  }
  .pef-switch-slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background-color: var(--walnut-200, hsl(30 14% 86%));
    transition: 0.2s;
    border-radius: 9999px;
  }
  .pef-switch-slider::before {
    content: "";
    position: absolute;
    height: 18px;
    width: 18px;
    left: 2px;
    bottom: 2px;
    background: #fff;
    transition: 0.2s;
    border-radius: 5px;
    box-shadow: 0 2px 4px 0 rgba(0,35,11,0.18);
  }
  .pef-switch input:checked + .pef-switch-slider {
    background: var(--ochre-500, hsl(35 85% 50%));
  }
  .pef-switch input:checked + .pef-switch-slider::before {
    transform: translateX(22px);
  }
  .pef-switch input:disabled + .pef-switch-slider {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .pef-hint {
    margin-top: 6px;
    font-size: 12px;
    color: color-mix(in srgb, var(--walnut-500, hsl(24 10% 45%)) 90%, transparent);
    line-height: 1.6;
  }

  /* ---------- Actions ---------- */
  .pef-actions {
    margin-top: 32px;
    padding-top: 24px;
    border-top: 1px solid var(--hairline, hsl(30 14% 90%));
    display: flex;
    justify-content: flex-start;
  }

  /* ---------- Meta ---------- */
  .pef-meta {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .pef-meta-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    font-size: 14px;
  }
  .pef-meta-label {
    color: color-mix(in srgb, var(--walnut-600, hsl(24 10% 30%)) 85%, transparent);
  }
  .pef-meta-value {
    font-weight: 600;
    color: var(--walnut-800, hsl(24 10% 16%));
    font-variant-numeric: tabular-nums;
  }

  /* ---------- Toast ---------- */
  .pef-toast-host {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
    pointer-events: none;
  }
  .pef-toast {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    border-radius: 8px;
    background: var(--surface, #fff);
    box-shadow: 0 6px 16px 0 rgba(0,0,0,0.08), 0 3px 6px -4px rgba(0,0,0,0.12), 0 9px 28px 8px rgba(0,0,0,0.05);
    font-size: 14px;
    line-height: 1.57;
    animation: pef-toast-in 0.3s ease-out;
    pointer-events: auto;
    max-width: min(360px, calc(100vw - 48px));
  }
  .pef-toast-success {
    background: var(--sage-50, hsl(170 30% 96%));
    border: 1px solid var(--sage-200, hsl(170 40% 82%));
    color: var(--sage-700, hsl(170 40% 32%));
  }
  .pef-toast-success svg { color: var(--sage-600, hsl(170 60% 32%)); }
  .pef-toast-error {
    background: hsl(6 80% 97%);
    border: 1px solid hsl(6 60% 86%);
    color: hsl(6 60% 42%);
  }
  .pef-toast-error svg { color: hsl(6 65% 55%); }
  .pef-toast-info {
    background: var(--indigo-50, hsl(240 45% 96%));
    border: 1px solid var(--indigo-200, hsl(240 50% 86%));
    color: var(--indigo-700, hsl(240 45% 42%));
  }
  .pef-toast-info svg { color: var(--indigo-500, hsl(240 60% 50%)); }
  .pef-toast-leave {
    animation: pef-toast-out 0.28s ease-in forwards;
  }
  @keyframes pef-toast-in {
    from { opacity: 0; transform: translateX(32px); }
    to   { opacity: 1; transform: translateX(0); }
  }
  @keyframes pef-toast-out {
    from { opacity: 1; transform: translateX(0); }
    to   { opacity: 0; transform: translateX(32px); }
  }

  /* ---------- Dark Mode Overrides ---------- */
  :global(html.dark) .pef-header,
  :global(html[data-theme-mode="dark"]) .pef-header {
    background: hsl(30 6% 14%);
    border-bottom-color: hsl(30 8% 22%);
  }
  :global(html.dark) .pef-card,
  :global(html[data-theme-mode="dark"]) .pef-card {
    background: hsl(30 6% 15%);
    border-color: hsl(30 8% 22%);
  }
  :global(html.dark) .pef-card-header,
  :global(html[data-theme-mode="dark"]) .pef-card-header {
    border-bottom-color: hsl(30 8% 22%);
  }
  :global(html.dark) .pef-input,
  :global(html.dark) .pef-select,
  :global(html[data-theme-mode="dark"]) .pef-input,
  :global(html[data-theme-mode="dark"]) .pef-select {
    background: hsl(30 6% 18%);
    border-color: hsl(30 8% 24%);
    color: hsl(30 10% 92%);
  }
  :global(html.dark) .pef-actions,
  :global(html[data-theme-mode="dark"]) .pef-actions {
    border-top-color: hsl(30 8% 22%);
  }
</style>
