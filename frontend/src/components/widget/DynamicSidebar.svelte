<script lang="ts">
/**
 * 侧边栏动态组件 - 从 API 获取数据
 * 支持自定义 API 地址，方便接入第三方后端
 */
import I18nKey from "@i18n/i18nKey";
import { currentLang, i18n } from "@i18n/translation";
import { onMount } from "svelte";
import { formatDynamicDate } from "@/utils/date-utils";
import { url } from "@/utils/url-utils";

interface DynamicEntry {
	id: string;
	published: number;
	html: string;
	images?: Array<{ alt: string; src: string; title?: string }>;
	searchText?: string;
	pinned?: boolean;
}

interface MemosConfig {
	enable: boolean;
	apiUrl: string;
	parent?: string;
}

interface Props {
	apiUrl: string;
	limit: number;
	memos?: MemosConfig;
}

let { apiUrl, limit, memos }: Props = $props();

let entries: DynamicEntry[] = $state([]);
let totalCount = $state(0);
let loading = $state(true);
let error = $state(false);

// 让 Svelte 模板里 `i18n(...)` 的调用响应语言切换：
// i18n() 本身是纯函数，不追踪 store；这里显式订阅 currentLang 触发模板重渲染。
// 注意：变量名不能用 "$" —— Svelte 中 "$" 前缀是保留字（rune / store 解包），
// vite-plugin-svelte 会报 "dollar_binding_invalid"。改用合法名字 langChangeTick。
const langChangeTick = $derived($currentLang);

function getBackendLang(): string {
	// 与 translation.ts readEffectiveLangHintRaw 保持一致：
	// cookie rosetta_lang → localStorage.lang → html[data-lang] → siteConfig.lang 最后兜底 zh_CN → "zh"
	const direct: string[] = [];
	if (typeof document !== "undefined") {
		const m = /(?:^|;\s*)rosetta_lang=([^;]+)/.exec(document.cookie || "");
		if (m && m[1]) {
			try { direct.push(decodeURIComponent(m[1])); } catch (_e) { /* ignore */ }
		}
		const attr = document.documentElement.getAttribute("data-lang");
		if (attr) direct.push(attr);
	}
	if (typeof localStorage !== "undefined") {
		const fromLs = localStorage.getItem("lang");
		if (fromLs) direct.push(fromLs);
	}
	for (const raw of direct) {
		const lang = String(raw || "").toLowerCase();
		if (!lang) continue;
		if (lang === "zh_tw" || lang === "zh_hant") return "zh_Hant";
		if (lang === "en") return "en";
		if (lang === "ja") return "ja";
		if (lang.startsWith("zh")) return "zh";
	}
	return "zh";
}

function resolveContent(content: any, backendLang: string): string {
	if (typeof content === "string") return content || "";
	if (typeof content === "object" && content !== null) {
		// 后端 key 统一为 zh / en / ja / zh_Hant
		return (
			content[backendLang] ||
			content.zh ||
			content.en ||
			content.ja ||
			Object.values(content).find(
				(v: any) => typeof v === "string" && v.length > 0,
			) ||
			""
		);
	}
	return "";
}

// 动态请求控制器：切语言 / 页面卸载 时 abort 未完成请求，避免浏览器刷 ERR_ABORTED 日志
let loadController: AbortController | null = null;
let reloadTimer: ReturnType<typeof setTimeout> | null = null;

function isGlobalUnloadingSoon(): boolean {
	if (typeof window === "undefined") return false;
	const w = window as Window & { __rosettaUnloadingSoon?: boolean };
	return !!w.__rosettaUnloadingSoon;
}

// 收到 rosetta-lang-change 且 detail.willReload=true 时置位，
// 代表整页 reload 即将发生（LangSwitcher.svelte 约 30ms 后调用 location.replace），
// 后续任何逻辑都不能再发新请求 / 排期 debounce，
// 同时必须立即 abort 进行中的请求，避免浏览器记录 ERR_ABORTED 日志。
// 注意：必须声明在 loadDynamics() 之前，以便函数内早期 return 生效。
let unloadingSoon = false;

async function loadDynamics() {
	if (unloadingSoon || isGlobalUnloadingSoon()) return;
	// 若之前的请求还没完成，先 cancel，避免旧结果覆盖新结果
	if (loadController) {
		try { loadController.abort(); } catch (_e) { /* ignore */ }
		loadController = null;
	}
	if (unloadingSoon || isGlobalUnloadingSoon()) return;
	loading = true;
	error = false;
	try {
		let data: DynamicEntry[];
		if (memos?.enable) {
			if (unloadingSoon || isGlobalUnloadingSoon()) return;
			const { fetchMemos } = await import("@/utils/memos-adapter");
			data = await fetchMemos(memos.apiUrl, { parent: memos.parent });
		} else {
			const backendLang = getBackendLang();
			if (unloadingSoon || isGlobalUnloadingSoon()) return;
			const ctrl = new AbortController();
			loadController = ctrl;
			// 后端可能没启动（纯 SSG mock 数据模式本地开发），
			// 这里给 6s 超时，避免挂太久；超时/被代理拒绝都按空数组兜底。
			const timeoutId = setTimeout(() => {
				try { ctrl.abort(); } catch (_e) { /* ignore */ }
			}, 6000);
			try {
				if (unloadingSoon || isGlobalUnloadingSoon()) {
					try { ctrl.abort(); } catch (_e) { /* ignore */ }
					return;
				}
				const res = await fetch(
					`/api/activities?page=1&page_size=50&lang=${encodeURIComponent(backendLang)}`,
					{ credentials: "same-origin", signal: ctrl.signal },
				);
				if (unloadingSoon || isGlobalUnloadingSoon()) return;
				if (!res.ok) {
					data = [];
				} else {
					const result = await res.json();
					const dynamics = Array.isArray(result?.items) ? result.items : [];
					data = dynamics.map((d: any) => ({
						id: String(d.id),
						published: new Date(d.created_at).getTime(),
						html: resolveContent(d.content, backendLang),
						images: Array.isArray(d.images)
							? d.images.map((src: string) => ({ alt: "", src }))
							: [],
						searchText: "",
						pinned: !!d.is_pinned,
					}));
				}
			} finally {
				clearTimeout(timeoutId);
			}
		}

		if (unloadingSoon || isGlobalUnloadingSoon()) return;
		totalCount = data.length;
		entries = data.slice(0, limit);
		updateCountBadge();
	} catch (e: any) {
		// AbortError / 后端未启动代理拒绝 / 网络超时 → 全部静默兜底，
		// 不把 "没后端" 的诊断噪音抛到用户控制台。
		const isAbort = e?.name === "AbortError" || (e as any)?.code === 20;
		if (!isAbort && !unloadingSoon && !isGlobalUnloadingSoon()) {
			console.debug("[DynamicSidebar] dynamics fallback to empty:", e?.message || e);
		}
		error = false;
		entries = [];
		totalCount = 0;
	} finally {
		loadController = null;
		if (!unloadingSoon && !isGlobalUnloadingSoon()) loading = false;
	}
}

onMount(() => {
	if (isGlobalUnloadingSoon()) {
		unloadingSoon = true;
		loading = false;
		return;
	}
	loadDynamics();
	let rafId: number | null = null;
	const onLangChange = (e: Event) => {
		const willReload = Boolean((e as CustomEvent)?.detail?.willReload);
		// 即将整页 reload：
		//   - 清空所有已排期的定时器
		//   - 立即中断正在进行的 fetch
		//   - 置位 unloadingSoon，后续永远不再发起新请求
		if (willReload) {
			unloadingSoon = true;
			if (reloadTimer) { clearTimeout(reloadTimer); reloadTimer = null; }
			if (rafId != null) { cancelAnimationFrame(rafId); rafId = null; }
			if (loadController) {
				try { loadController.abort(); } catch (_e) { /* ignore */ }
				loadController = null;
			}
			return;
		}
		// 非 reload 场景（纯前端运行时语言切换，目前项目里不会出现）：
		// 走 250ms debounce + pendingReload 检测，再发请求。
		if (unloadingSoon || isGlobalUnloadingSoon()) return;
		if (reloadTimer) clearTimeout(reloadTimer);
		if (rafId != null) cancelAnimationFrame(rafId);
		reloadTimer = setTimeout(() => {
			rafId = requestAnimationFrame(() => {
				if (unloadingSoon || isGlobalUnloadingSoon()) return;
				const pendingReload = /[?&]_lang_reload=/.test(window.location.search);
				if (!pendingReload) loadDynamics();
			});
		}, 250);
	};
	window.addEventListener("rosetta-lang-change", onLangChange);
	// 页面卸载 / 隐藏 时中断未完成请求，减少 Abort 噪音
	const cleanup = () => {
		unloadingSoon = true;
		if (reloadTimer) { clearTimeout(reloadTimer); reloadTimer = null; }
		if (loadController) {
			try { loadController.abort(); } catch (_e) { /* ignore */ }
			loadController = null;
		}
	};
	window.addEventListener("beforeunload", cleanup);
	window.addEventListener("pagehide", cleanup);
	return () => {
		window.removeEventListener("rosetta-lang-change", onLangChange);
		window.removeEventListener("beforeunload", cleanup);
		window.removeEventListener("pagehide", cleanup);
		cleanup();
	};
});

function updateCountBadge() {
	const badge = document.querySelector("[data-dynamic-count]");
	if (badge && totalCount > 0) {
		badge.textContent = `(${totalCount})`;
	}
}

// 从 HTML 中提取纯文本摘要
function getPlainText(html: string): string {
	const div = document.createElement("div");
	div.innerHTML = html;
	return div.textContent?.trim() || "";
}

// 格式化日期
// 本地 API 使用 formatDynamicDate（带时区转换）
// 第三方 API 和 Memos 使用浏览器本地时区，不做额外转换
function formatDate(timestamp: number): string {
	if (apiUrl.startsWith("http") || memos?.enable) {
		return new Date(timestamp).toLocaleDateString("zh-CN", {
			year: "numeric",
			month: "2-digit",
			day: "2-digit",
			hour: "2-digit",
			minute: "2-digit",
		});
	}
	return formatDynamicDate(new Date(timestamp));
}
</script>

<div class="flex flex-col gap-1.5">
	{#if loading}
		<div class="flex justify-center p-3">
			<svg class="size-5 animate-spin text-(--primary)" viewBox="0 0 24 24" fill="none">
				<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.25"/>
				<path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
			</svg>
		</div>
	{:else if error || entries.length === 0}
		<p
			class="m-0 p-3 text-center text-sm text-neutral-500"
			data-i18n-text-key={I18nKey.dynamicEmpty}
		>
			{i18n(I18nKey.dynamicEmpty)}
		</p>
	{:else}
		{#each entries as entry (entry.id)}
			{@const text = getPlainText(entry.html)}
			{@const image = entry.images?.[0]}
			<!-- label-content-name-mismatch 修复：不手动传 aria-label，
			     让链接内部可见文本（日期 + 摘要文本）直接作为 accessible name，
			     避免 axe-core 判定 aria-label 与可见文本结构不一致。 -->
			<a
				href={url(`/dynamic/#dynamic-${entry.id}`)}
				class="group flex min-w-0 min-h-16 items-center gap-3 rounded-lg p-2
					text-neutral-700/75 dark:text-neutral-300/75
					hover:bg-(--btn-plain-bg-hover) hover:text-(--primary)
					active:bg-(--btn-plain-bg-active) transition-colors duration-150"
			>
				<div class="min-w-0 flex-1">
					<div class="mb-1 flex items-center gap-1 text-xs leading-4 text-(--primary)">
						<svg class="size-4 shrink-0" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
							<path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
						</svg>
						<time datetime={new Date(entry.published).toISOString()}>
							{formatDate(entry.published)}
						</time>
						{#if entry.pinned}
							<span
								class="ml-auto inline-flex items-center gap-0.5 text-[10px] px-1 py-0.5 rounded bg-(--primary)/10 text-(--primary) font-medium"
								title={i18n(I18nKey.pinned)}
								data-i18n-title-key={I18nKey.pinned}
							>
								<svg class="size-3" fill="currentColor" viewBox="0 0 24 24"><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2z"/></svg>
								<span data-i18n-text-key={I18nKey.pinned}>{i18n(I18nKey.pinned)}</span>
							</span>
						{/if}
					</div>
					<p class="m-0 line-clamp-3 text-sm leading-[1.35rem]">
						{text}
					</p>
				</div>
				{#if image}
					<img
						src={image.src}
						alt={image.alt}
						class="size-14 shrink-0 rounded-lg bg-(--btn-plain-bg-hover) object-cover"
						loading="lazy"
						decoding="async"
					/>
				{/if}
			</a>
		{/each}
	{/if}
</div>
