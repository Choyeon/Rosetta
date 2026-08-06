<script lang="ts">
/**
 * 侧边栏动态组件 - 从 API 获取数据
 * 支持自定义 API 地址，方便接入第三方后端
 */
import I18nKey from "@i18n/i18nKey";
import { i18n } from "@i18n/translation";
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

function getBackendLang(): string {
	const lang = (
		typeof localStorage !== "undefined"
			? localStorage.getItem("lang") || "zh_CN"
			: "zh_CN"
	).toLowerCase();
	if (lang === "zh_tw" || lang === "zh_hant") return "zh_Hant";
	if (lang === "en") return "en";
	if (lang === "ja") return "ja";
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

async function loadDynamics() {
	loading = true;
	error = false;
	try {
		let data: DynamicEntry[];
		if (memos?.enable) {
			const { fetchMemos } = await import("@/utils/memos-adapter");
			data = await fetchMemos(memos.apiUrl, { parent: memos.parent });
		} else {
			const backendLang = getBackendLang();
			const res = await fetch(
				`/api/activities?page=1&page_size=50&lang=${encodeURIComponent(backendLang)}`,
				{ credentials: "same-origin" },
			);
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
		}

		totalCount = data.length;
		entries = data.slice(0, limit);
		updateCountBadge();
	} catch (e) {
		console.warn("[DynamicSidebar] Failed to load dynamics:", e);
		error = false;
	} finally {
		loading = false;
	}
}

onMount(() => {
	loadDynamics();
	// 监听语言切换，重新加载动态内容
	window.addEventListener("rosetta-lang-change", loadDynamics);
	return () => {
		window.removeEventListener("rosetta-lang-change", loadDynamics);
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
		<p class="m-0 p-3 text-center text-sm text-neutral-500">
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
							<span class="ml-auto inline-flex items-center gap-0.5 text-[10px] px-1 py-0.5 rounded bg-(--primary)/10 text-(--primary) font-medium">
								<svg class="size-3" fill="currentColor" viewBox="0 0 24 24"><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2z"/></svg>
								{i18n(I18nKey.pinned)}
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
