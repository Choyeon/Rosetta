<script lang="ts">
import { onMount, tick } from "svelte";
import { getBackendLang } from "@/api/client";
import ClientPagination from "@/components/common/ClientPagination.svelte";
import { formatTimezoneOffset } from "@/utils/date-utils";
import { fetchMemos } from "@/utils/memos-adapter";
import { registerDynamicGallery } from "./dynamic-gallery";
import { registerDynamicInlineComments } from "./dynamic-inline-comments";

type DynamicImage = {
	alt: string;
	src: string;
	title?: string;
};

type DynamicData = {
	id: string;
	published: number;
	html: string;
	images: DynamicImage[];
	searchText: string;
	pinned?: boolean;
	location?: string;
};

interface MemosConfig {
	enable: boolean;
	apiUrl: string;
	parent?: string;
}

interface Props {
	source: string;
	itemsPerPage: number;
	showComments: boolean;
	emptyText: string;
	noResultsText: string;
	loadingText: string;
	allYearsText: string;
	timezone: string;
	memos?: MemosConfig;
}

const {
	source,
	itemsPerPage,
	showComments,
	emptyText,
	noResultsText,
	loadingText,
	allYearsText,
	timezone,
	memos,
}: Props = $props();

let entries = $state<DynamicData[]>([]);
let filtered = $state<DynamicData[]>([]);
let currentPage = $state(1);
let loading = $state(true);
let failed = $state(false);
let templateReady = $state(false);
let list: HTMLElement;
let template: HTMLTemplateElement | null = null;
let searchInput: HTMLInputElement | null = null;
let yearSelect: HTMLSelectElement | null = null;
let restoreAnchorAfterRender = false;

// 与 DynamicSidebar 同一套保护机制：
//   rosetta-lang-change.willReload → 立即 cancel 所有请求 + 排期 + 拒绝后续 I/O
//   beforeunload/pagehide → 同样 abort
// 避免浏览器控制台出现 "ERR_ABORTED" 网络错误日志。
let feedLoadController: AbortController | null = null;
let feedUnloadingSoon = false;

function isFeedGlobalUnloadingSoon(): boolean {
	if (typeof window === "undefined") return false;
	const w = window as Window & { __rosettaUnloadingSoon?: boolean };
	return !!w.__rosettaUnloadingSoon;
}

function resolveContent(content: any, backendLang: string): string {
	if (typeof content === "string") return content || "";
	if (typeof content === "object" && content !== null) {
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

const pageEntries = $derived(
	filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage),
);

function pageFromUrl() {
	return Math.max(
		1,
		Number(new URL(window.location.href).searchParams.get("page")) || 1,
	);
}

function updateUrl(clearHash = false) {
	const current = new URL(window.location.href);
	if (currentPage > 1) current.searchParams.set("page", String(currentPage));
	else current.searchParams.delete("page");
	if (clearHash) current.hash = "";
	history.replaceState(history.state, "", current);
}

function applyFilters(resetPage = true) {
	const query = searchInput?.value.toLocaleLowerCase().trim() || "";
	const year = yearSelect?.value || "all";
	filtered = entries.filter(
		(entry) =>
			(year === "all" ||
				String(new Date(entry.published).getUTCFullYear()) === year) &&
			(!query || entry.searchText.includes(query)),
	);
	if (resetPage) currentPage = 1;
	const totalPages = Math.max(1, Math.ceil(filtered.length / itemsPerPage));
	currentPage = Math.min(currentPage, totalPages);
	updateUrl(resetPage);
}

function populateYears() {
	if (!yearSelect) return;
	yearSelect.replaceChildren();
	const all = document.createElement("option");
	all.value = "all";
	all.textContent = allYearsText;
	yearSelect.append(all);
	const years = [
		...new Set(
			entries.map((entry) => new Date(entry.published).getUTCFullYear()),
		),
	];
	for (const year of years) {
		const option = document.createElement("option");
		option.value = String(year);
		option.textContent = String(year);
		yearSelect.append(option);
	}
}

function createItem(entry: DynamicData) {
	if (!template) return null;
	const fragment = template.content.cloneNode(true) as DocumentFragment;
	const root = fragment.querySelector<HTMLElement>("[data-dynamic-entry]");
	if (!root) return null;
	const anchorId = `dynamic-${entry.id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
	const permalinkUrl = new URL(window.location.href);
	permalinkUrl.hash = anchorId;
	const permalink = `${permalinkUrl.pathname}${permalinkUrl.search}${permalinkUrl.hash}`;
	root.id = anchorId;
	root.dataset.year = String(new Date(entry.published).getUTCFullYear());

	const author = root.querySelector<HTMLElement>("[data-dynamic-author]");
	if (author) {
		author.id = `${anchorId}-author`;
		root.querySelector("article")?.setAttribute("aria-labelledby", author.id);
	}
	root
		.querySelectorAll<HTMLAnchorElement>("[data-dynamic-permalink]")
		.forEach((link) => {
			link.href = permalink;
			link.dataset.noSwup = "";
			link.addEventListener("click", (event) => {
				if (
					event.button !== 0 ||
					event.metaKey ||
					event.ctrlKey ||
					event.shiftKey ||
					event.altKey
				)
					return;
				event.preventDefault();
				event.stopPropagation();
				history.replaceState(history.state, "", permalink);
			});
		});
	const time = root.querySelector<HTMLTimeElement>("[data-dynamic-time]");
	if (time) {
		const date = new Date(entry.published);
		time.dateTime = date.toISOString();
		// 第三方 API 和 Memos 使用浏览器本地时区，不做额外时区转换
		if (source.startsWith("http") || memos?.enable) {
			time.textContent = date.toLocaleDateString("zh-CN", {
				year: "numeric",
				month: "2-digit",
				day: "2-digit",
				hour: "2-digit",
				minute: "2-digit",
			});
		} else {
			time.textContent = new Intl.DateTimeFormat(
				document.documentElement.lang || undefined,
				{
					timeZone: "UTC",
					year: "numeric",
					month: "2-digit",
					day: "2-digit",
					hour: "2-digit",
					minute: "2-digit",
					second: "2-digit",
				},
			).format(date);
			time.textContent += ` ${formatTimezoneOffset(timezone, date)}`;
		}
	}
	const location = root.querySelector<HTMLElement>("[data-dynamic-location]");
	if (location) {
		const locationText = entry.location?.trim();
		if (locationText) {
			const text = location.querySelector<HTMLElement>(
				"[data-dynamic-location-text]",
			);
			if (text) text.textContent = locationText;
			location.title = locationText;
			location.removeAttribute("hidden");
		} else {
			location.setAttribute("hidden", "");
		}
	}

	const content = root.querySelector<HTMLElement>("[data-dynamic-content]");
	if (content) {
		content.id = `${anchorId}-content`;
		content.innerHTML = entry.html;
		for (const image of entry.images) {
			const element = document.createElement("img");
			element.src = image.src;
			element.alt = image.alt;
			element.loading = "lazy";
			if (image.title) element.title = image.title;
			content.append(element);
		}
		const gallery = root.querySelector<HTMLElement>("dynamic-gallery");
		if (gallery) gallery.dataset.sourceId = content.id;
	}

	// 置顶标识
	const pinned = root.querySelector<HTMLElement>("[data-dynamic-pinned]");
	if (pinned) {
		if (entry.pinned) {
			pinned.removeAttribute("hidden");
		} else {
			pinned.setAttribute("hidden", "");
		}
	}

	const comments = root.querySelector<HTMLElement>("dynamic-inline-comments");
	if (comments) {
		if (showComments) {
			comments.dataset.src = `/dynamic/comments/?path=${encodeURIComponent(
				`/dynamic/${entry.id}/`,
			)}`;
		} else {
			comments.remove();
		}
	}
	return fragment;
}

async function renderItems(items: DynamicData[]) {
	await tick();
	if (!list || !template) return;
	list.replaceChildren();
	for (const entry of items) {
		const item = createItem(entry);
		if (item) list.append(item);
	}
	if (restoreAnchorAfterRender) {
		restoreAnchorAfterRender = false;
		const target = document.getElementById(
			decodeURIComponent(window.location.hash.slice(1)),
		);
		target?.scrollIntoView({ behavior: "auto", block: "start" });
	}
}

function goToPage(page: number) {
	currentPage = page;
	updateUrl(true);
	document
		.querySelector(".dynamic-page")
		?.scrollIntoView({ behavior: "smooth", block: "start" });
}

$effect(() => {
	if (!templateReady) return;
	renderItems(pageEntries);
});

onMount(() => {
	registerDynamicGallery();
	registerDynamicInlineComments();
	const page = list.closest(".dynamic-page");
	template =
		page?.querySelector<HTMLTemplateElement>("[data-dynamic-item-template]") ??
		null;
	templateReady = template !== null;
	searchInput =
		page?.querySelector<HTMLInputElement>("[data-dynamic-search]") ?? null;
	yearSelect =
		page?.querySelector<HTMLSelectElement>("[data-year-select]") ?? null;
	const filter = () => applyFilters();
	searchInput?.addEventListener("input", filter);
	yearSelect?.addEventListener("change", filter);

	const cleanupAbort = () => {
		feedUnloadingSoon = true;
		if (feedLoadController) {
			try { feedLoadController.abort(); } catch (_e) { /* ignore */ }
			feedLoadController = null;
		}
	};

	const onLangChange = (e: Event) => {
		const willReload = Boolean((e as CustomEvent)?.detail?.willReload);
		if (!willReload) return;
		cleanupAbort();
	};
	window.addEventListener("rosetta-lang-change", onLangChange);
	window.addEventListener("beforeunload", cleanupAbort);
	window.addEventListener("pagehide", cleanupAbort);

	const load = async () => {
		if (feedUnloadingSoon || isFeedGlobalUnloadingSoon()) return;
		try {
			if (memos?.enable) {
				if (feedUnloadingSoon || isFeedGlobalUnloadingSoon()) return;
				entries = await fetchMemos(memos.apiUrl, { parent: memos.parent });
			} else {
				const backendLang = getBackendLang(
					typeof localStorage !== "undefined"
						? localStorage.getItem("lang") || "zh_CN"
						: "zh_CN",
				);
				// 构造带分页参数的URL（注意：后端page_size最大限制为100）
				const MAX_PAGE_SIZE = 100;
				let requestUrl = source;
				try {
					const u = new URL(source, window.location.origin);
					if (!u.searchParams.has("page")) u.searchParams.set("page", "1");
					if (!u.searchParams.has("page_size"))
						u.searchParams.set("page_size", String(MAX_PAGE_SIZE));
					if (!u.searchParams.has("lang"))
						u.searchParams.set("lang", backendLang);
					requestUrl = u.toString();
				} catch {
					// 相对URL，手动拼接参数
					const sep = source.includes("?") ? "&" : "?";
					requestUrl = `${source}${sep}page=1&page_size=${MAX_PAGE_SIZE}&lang=${encodeURIComponent(backendLang)}`;
				}
				if (feedUnloadingSoon || isFeedGlobalUnloadingSoon()) return;
				const ctrl = new AbortController();
				feedLoadController = ctrl;
				try {
					const response = await fetch(requestUrl, {
						credentials: "same-origin",
						signal: ctrl.signal,
					});
					if (feedUnloadingSoon || isFeedGlobalUnloadingSoon()) return;
					if (!response.ok) throw new Error(`HTTP ${response.status}`);
					const result = await response.json();
					if (feedUnloadingSoon || isFeedGlobalUnloadingSoon()) return;
					// 正确处理分页对象：{ items: [...], total, page }
					const rawItems = Array.isArray(result?.items)
						? result.items
						: Array.isArray(result)
							? result
							: [];
					entries = rawItems.map((d: any) => ({
						id: String(d.id ?? ""),
						published: d.created_at
							? new Date(d.created_at).getTime()
							: d.published || Date.now(),
						html: resolveContent(d.content ?? d.html, backendLang),
						images: Array.isArray(d.images)
							? d.images.map((img: any) =>
									typeof img === "string"
										? { alt: "", src: img }
										: {
												alt: img.alt || "",
												src: img.src || "",
												title: img.title,
											},
								)
							: [],
						searchText: "",
						pinned: !!d.is_pinned || !!d.pinned,
						location: typeof d.location === "string" ? d.location : undefined,
					}));
				} finally {
					feedLoadController = null;
				}
			}
			if (feedUnloadingSoon || isFeedGlobalUnloadingSoon()) return;
			// 更新页面计数
			const countEl = document.querySelector("[data-dynamic-page-count]");
			if (countEl) countEl.textContent = String(entries.length);
			populateYears();
			currentPage = pageFromUrl();
			applyFilters(false);
			const anchorId = decodeURIComponent(window.location.hash.slice(1));
			if (anchorId) {
				const anchorIndex = filtered.findIndex(
					(entry) =>
						`dynamic-${entry.id.replace(/[^a-zA-Z0-9_-]/g, "-")}` === anchorId,
				);
				if (anchorIndex >= 0) {
					currentPage = Math.floor(anchorIndex / itemsPerPage) + 1;
					updateUrl();
					restoreAnchorAfterRender = true;
				}
			}
		} catch (error) {
			const isAbort = (error as any)?.name === "AbortError" || (error as any)?.code === 20;
			if (isAbort || feedUnloadingSoon || isFeedGlobalUnloadingSoon()) {
				// 即将 reload / 主动 abort：静默，不输出任何错误日志，避免 ERR_ABORTED 噪音
				failed = false;
			} else {
				console.error("Failed to load dynamics", error);
				failed = true;
			}
		} finally {
			if (!feedUnloadingSoon && !isFeedGlobalUnloadingSoon()) loading = false;
		}
	};
	if (isFeedGlobalUnloadingSoon()) {
		cleanupAbort();
		return () => {
			window.removeEventListener("rosetta-lang-change", onLangChange);
			window.removeEventListener("beforeunload", cleanupAbort);
			window.removeEventListener("pagehide", cleanupAbort);
		};
	}
	void load();

	return () => {
		window.removeEventListener("rosetta-lang-change", onLangChange);
		window.removeEventListener("beforeunload", cleanupAbort);
		window.removeEventListener("pagehide", cleanupAbort);
		searchInput?.removeEventListener("input", filter);
		yearSelect?.removeEventListener("change", filter);
		cleanupAbort();
	};
});
</script>

{#if loading}
	<div class="dynamic-loading card-base" role="status">
		<span class="dynamic-loading-spinner" aria-hidden="true"></span>
		<p>{loadingText}</p>
	</div>
{:else if failed || entries.length === 0}
	<div class="dynamic-empty card-base">
		<p>{emptyText}</p>
	</div>
{:else if filtered.length === 0}
	<div class="dynamic-no-results card-base">
		<p>{noResultsText}</p>
	</div>
{/if}

<div class="dynamic-feed" bind:this={list}></div>

{#if !loading && !failed}
	<ClientPagination
		totalItems={filtered.length}
		{itemsPerPage}
		{currentPage}
		onPageChange={goToPage}
	/>
{/if}
