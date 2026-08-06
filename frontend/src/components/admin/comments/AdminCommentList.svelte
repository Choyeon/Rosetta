<script lang="ts">
import { onMount, tick } from "svelte";
import {
	type AdminComment,
	type AdminCommentStatus,
	approveComment,
	batchAdminComments,
	type CommentBatchAction,
	deleteComment,
	type GetAdminCommentsParams,
	getAdminComments,
	markCommentSpam,
	rejectComment,
	restoreComment,
} from "@/api/admin";
import type { CommentResponse } from "@/api/schema-contract";

type TabKey = "pending" | "approved" | "rejected" | "spam" | "all";

interface Toast {
	id: number;
	type: "success" | "error";
	message: string;
}

let loading = false;
let error: Error | null = null;

let page = 1;
let pageSize = 20;
let total = 0;
let items: (AdminComment | CommentResponse)[] = [];
let counts: Record<TabKey, number> = {
	pending: 0,
	approved: 0,
	rejected: 0,
	spam: 0,
	all: 0,
};

let status: TabKey = "pending";
let keyword = "";
let debouncedKeyword = "";
let searchTimer: number | null = null;

let selectedIds: Set<number> = new Set();
let expandedIds: Set<number> = new Set();
let hoverStatusId: number | null = null;

let pageInput = "";
let pageSizeOptions = [10, 20, 50, 100];
let toasts: Toast[] = [];
let toastIdSeq = 0;
let commentCountResponseFetched = false;

const totalPages = () => Math.max(1, Math.ceil(total / pageSize));
const startIdx = () => (total === 0 ? 0 : (page - 1) * pageSize + 1);
const endIdx = () => Math.min(page * pageSize, total);

const allSelected = () =>
	items.length > 0 && items.every((c) => selectedIds.has(c.id));
const someSelected = () => items.some((c) => selectedIds.has(c.id));

const tabs: { key: TabKey; label: string }[] = [
	{ key: "pending", label: "待审核" },
	{ key: "approved", label: "已通过" },
	{ key: "rejected", label: "已拒绝" },
	{ key: "spam", label: "垃圾" },
	{ key: "all", label: "全部" },
];

const batchActions: {
	key: CommentBatchAction;
	label: string;
	confirm: string;
}[] = [
	{ key: "approve", label: "通过", confirm: "确认批量通过选中的评论？" },
	{ key: "reject", label: "拒绝", confirm: "确认批量拒绝选中的评论？" },
	{ key: "spam", label: "标垃圾", confirm: "确认将选中的评论标记为垃圾？" },
	{
		key: "delete",
		label: "删除",
		confirm: "确认批量删除选中的评论？此操作不可恢复。",
	},
];

function showToast(type: Toast["type"], message: string) {
	const id = ++toastIdSeq;
	toasts.push({ id, type, message });
	setTimeout(() => {
		toasts = toasts.filter((t) => t.id !== id);
	}, 2800);
}

function actionLabel(a: CommentBatchAction): string {
	switch (a) {
		case "approve":
			return "通过";
		case "reject":
			return "拒绝";
		case "spam":
			return "标记为垃圾";
		case "restore":
			return "恢复";
		case "delete":
			return "删除";
		default:
			return a;
	}
}

function formatDate(iso?: string | null): string {
	if (!iso) return "-";
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	const pad = (n: number) => String(n).padStart(2, "0");
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function statusFromItem(c: AdminComment | CommentResponse): AdminCommentStatus {
	if ("status" in c && c.status) return c.status as AdminCommentStatus;
	if ("is_approved" in c) {
		return c.is_approved ? "approved" : "pending";
	}
	return "pending";
}

function statusBadgeClass(s: AdminCommentStatus): string {
	switch (s) {
		case "pending":
			return "badge-pending";
		case "approved":
			return "badge-approved";
		case "rejected":
			return "badge-rejected";
		case "spam":
			return "badge-spam";
		default:
			return "";
	}
}

function statusLabel(s: AdminCommentStatus): string {
	switch (s) {
		case "pending":
			return "待审核";
		case "approved":
			return "已通过";
		case "rejected":
			return "已拒绝";
		case "spam":
			return "垃圾";
		default:
			return s;
	}
}

function nicknameOf(c: AdminComment | CommentResponse): string {
	const u =
		("user" in c ? c.user : null) || ("user_ref" in c ? c.user_ref : null);
	if (u && (u.nickname || u.username)) return u.nickname || u.username;
	if ("author_name" in c && c.author_name) return c.author_name;
	return "匿名";
}

function isAnonymous(c: AdminComment | CommentResponse): boolean {
	const u =
		("user" in c ? c.user : null) || ("user_ref" in c ? c.user_ref : null);
	return !u;
}

function avatarUrl(c: AdminComment | CommentResponse): string | null {
	const resolved = "resolved_avatar_url" in c ? c.resolved_avatar_url : null;
	if (resolved)
		return `/api/avatar/by-url?src=${encodeURIComponent(resolved)}&size=72`;
	const u =
		("user" in c ? c.user : null) || ("user_ref" in c ? c.user_ref : null);
	if (u?.avatar)
		return `/api/avatar/by-url?src=${encodeURIComponent(u.avatar)}&size=72`;
	return null;
}

function letterInitial(c: AdminComment | CommentResponse): string {
	const name = nicknameOf(c);
	return (name?.trim()?.[0] ?? "?").toUpperCase();
}

function letterBg(name: string): string {
	const palette = [
		"#f59e0b",
		"#10b981",
		"#3b82f6",
		"#ef4444",
		"#8b5cf6",
		"#ec4899",
		"#14b8a6",
		"#f97316",
	];
	let hash = 0;
	for (let i = 0; i < name.length; i++)
		hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
	return palette[hash % palette.length];
}

function contentTruncated(c: AdminComment | CommentResponse): string {
	const raw = c.content ?? "";
	if (raw.length <= 80) return raw;
	return `${raw.slice(0, 80)}…`;
}

function isExpanded(c: AdminComment | CommentResponse): boolean {
	return expandedIds.has(c.id);
}

function toggleExpand(c: AdminComment | CommentResponse) {
	if (c.content.length <= 80) return;
	if (expandedIds.has(c.id)) expandedIds.delete(c.id);
	else expandedIds.add(c.id);
	expandedIds = new Set(expandedIds);
}

async function loadCountsOnce() {
	if (commentCountResponseFetched) return;
	try {
		const res = await getAdminComments({
			page: 1,
			page_size: 1,
			status: "all",
		});
		counts.all = res.total || 0;
		commentCountResponseFetched = true;
		const keys: TabKey[] = ["pending", "approved", "rejected", "spam"];
		await Promise.all(
			keys.map(async (k) => {
				try {
					const r = await getAdminComments({
						page: 1,
						page_size: 1,
						status: k as AdminCommentStatus,
					});
					counts[k] = r.total || 0;
				} catch {
					/* ignore */
				}
			}),
		);
	} catch {
		/* ignore */
	}
}

async function reload() {
	loading = true;
	error = null;
	try {
		const params: GetAdminCommentsParams = {
			page,
			page_size: pageSize,
			status: status as AdminCommentStatus,
		};
		if (debouncedKeyword.trim()) params.keyword = debouncedKeyword.trim();

		const res = await getAdminComments(params);
		items = res.items ?? [];
		total = res.total ?? 0;
		counts.all = Math.max(counts.all, total);
		if (status !== "all") {
			counts[status] = Math.max(counts[status], total);
		}
		selectedIds.clear();
		selectedIds = new Set(selectedIds);
	} catch (e) {
		error = e instanceof Error ? e : new Error(String(e));
	} finally {
		loading = false;
	}
}

function switchStatus(s: TabKey) {
	if (status === s && !loading) return;
	status = s;
	page = 1;
	void reload();
}

function onKeywordInput(e: Event) {
	const target = e.target as HTMLInputElement;
	keyword = target.value;
	if (searchTimer) window.clearTimeout(searchTimer);
	searchTimer = window.setTimeout(() => {
		debouncedKeyword = keyword;
		page = 1;
		void reload();
	}, 400);
}

function toggleAll(e: Event) {
	const checked = (e.target as HTMLInputElement).checked;
	if (checked) {
		for (const c of items) selectedIds.add(c.id);
	} else {
		selectedIds.clear();
	}
	selectedIds = new Set(selectedIds);
}

function toggleOne(id: number, e: Event) {
	const checked = (e.target as HTMLInputElement).checked;
	if (checked) selectedIds.add(id);
	else selectedIds.delete(id);
	selectedIds = new Set(selectedIds);
}

async function runSingle(
	action: "approve" | "reject" | "spam" | "restore" | "delete",
	id: number,
	confirmMsg?: string,
) {
	if (confirmMsg && !window.confirm(confirmMsg)) return;
	try {
		switch (action) {
			case "approve":
				await approveComment(id);
				break;
			case "reject":
				await rejectComment(id);
				break;
			case "spam":
				await markCommentSpam(id);
				break;
			case "restore":
				await restoreComment(id);
				break;
			case "delete":
				await deleteComment(id);
				break;
		}
		showToast("success", `已${actionLabel(action)}评论 #${id}`);
		void reload();
		void loadCountsOnce();
	} catch (e) {
		const msg = e instanceof Error ? e.message : "操作失败";
		showToast("error", `操作失败：${msg}`);
	}
}

async function runBatch(action: CommentBatchAction) {
	const ids = Array.from(selectedIds);
	if (ids.length === 0) return;
	const def = batchActions.find((b) => b.key === action);
	const confirmMsg =
		def?.confirm ?? `确认批量${actionLabel(action)}选中的 ${ids.length} 条？`;
	if (!window.confirm(confirmMsg)) return;
	try {
		const r = await batchAdminComments(action, ids);
		const n =
			(r as { processed_count?: number })?.processed_count ?? ids.length;
		showToast("success", `已${actionLabel(action)} ${n} 条`);
		void reload();
		void loadCountsOnce();
	} catch (e) {
		const msg = e instanceof Error ? e.message : "操作失败";
		showToast("error", `批量操作失败：${msg}`);
	}
}

function changePage(p: number) {
	const tp = totalPages();
	if (p < 1 || p > tp || p === page) return;
	page = p;
	void reload();
}

function changePageSize(s: number) {
	if (s === pageSize) return;
	pageSize = s;
	page = 1;
	void reload();
}

function onPageSizeSelect(e: Event) {
	const val = Number((e.target as HTMLSelectElement).value);
	if (Number.isFinite(val)) changePageSize(val);
}

function gotoPageInput() {
	const n = Number(pageInput);
	if (!Number.isFinite(n)) return;
	pageInput = "";
	changePage(Math.floor(n));
}

function previewPost(c: AdminComment | CommentResponse) {
	const ref = "post_ref" in c ? c.post_ref : null;
	const slug = ref?.slug;
	const fallbackPostId = "post_id" in c ? c.post_id : null;
	const url = slug
		? `/post/${slug}`
		: fallbackPostId
			? `/post/${fallbackPostId}`
			: "";
	if (url) window.open(url, "_blank");
}

function editPost(c: AdminComment | CommentResponse) {
	const ref = "post_ref" in c ? c.post_ref : null;
	const id = ref?.id ?? ("post_id" in c ? c.post_id : null);
	if (id != null) window.open(`/admin/posts/${id}`, "_blank");
}

function postTitleOf(c: AdminComment | CommentResponse): string {
	const ref = "post_ref" in c ? c.post_ref : null;
	const pTitle =
		"post" in c
			? (c as { post?: { title?: string } | null }).post?.title
			: null;
	return (ref?.title ?? pTitle ?? "(未关联)") || "(未关联)";
}

onMount(() => {
	void loadCountsOnce();
	void reload();
});

interface PageItem {
	key: string;
	type: "num" | "ellipsis";
	value?: number;
}
function pageRange(current: number, total: number): PageItem[] {
	const out: PageItem[] = [];
	if (total <= 7) {
		for (let i = 1; i <= total; i++)
			out.push({ key: `p${i}`, type: "num", value: i });
		return out;
	}
	const delta = 2;
	const range: number[] = [];
	for (
		let i = Math.max(2, current - delta);
		i <= Math.min(total - 1, current + delta);
		i++
	) {
		range.push(i);
	}
	out.push({ key: "p1", type: "num", value: 1 });
	if (range[0] > 2) out.push({ key: `e1-${current}`, type: "ellipsis" });
	for (const i of range) out.push({ key: `p${i}`, type: "num", value: i });
	if (range[range.length - 1] < total - 1)
		out.push({ key: `e2-${current}`, type: "ellipsis" });
	out.push({ key: `p${total}`, type: "num", value: total });
	return out;
}
</script>

<div class="admin-comment-list">
	<!-- =============== Toolbar =============== -->
	<div class="admin-toolbar">
		<div class="filter-tabs">
			{#each tabs as t}
				{@const active = t.key === status}
				{@const showBadge = t.key !== "all"}
				<button
					type="button"
					class:list={["tab-btn", { "tab-active": active }]}
					onclick={() => switchStatus(t.key)}
				>
					<span>{t.label}</span>
					{#if showBadge}
						<span class="tab-badge">{counts[t.key]}</span>
					{/if}
				</button>
			{/each}
		</div>

		<div class="search-bar">
			<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
			<input
				type="text"
				placeholder="搜索内容/昵称/邮箱/QQ/GitHub/IP"
				value={keyword}
				oninput={onKeywordInput}
			/>
		</div>

		<div class:list={["batch-bar", { visible: selectedIds.size > 0 }]}>
			<span class="batch-count">已选 {selectedIds.size}</span>
			{#each batchActions as ba}
				<button
					type="button"
					class:list={[
						"btn",
						"btn-sm",
						ba.key === "approve" ? "btn-success" :
						ba.key === "reject" ? "btn-outline" :
						ba.key === "spam" ? "btn-outline" :
						"btn-danger",
					]}
					disabled={selectedIds.size === 0}
					onclick={() => runBatch(ba.key)}
				>
					{ba.label}
				</button>
			{/each}
		</div>
	</div>

	<!-- =============== Table =============== -->
	<div class="table-wrapper">
		<div class="table-scroll">
			<table class="admin-table">
				<thead>
					<tr>
						<th style="width:48px;">
							{#if !loading && !error}
								<label class="chk-wrap">
									<input
										type="checkbox"
										indeterminate={someSelected() && !allSelected()}
										checked={allSelected()}
										onchange={toggleAll}
									/>
									<span class="chk-box" />
								</label>
							{/if}
						</th>
						<th style="width:240px;">作者</th>
						<th>内容</th>
						<th style="width:220px;">关联文章</th>
						<th style="width:110px;">状态</th>
						<th style="width:160px;">时间</th>
						<th style="width:210px;">操作</th>
					</tr>
				</thead>
				<tbody>
					{#if error}
						<tr>
							<td colspan="7">
								<div class="error-box" onclick={() => reload()}>
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
									<div class="error-msg">加载失败，点击重试</div>
									<div class="error-sub">{error.message}</div>
								</div>
							</td>
						</tr>
					{:else if loading}
						{#each Array.from({ length: 6 }) as _, i}
							<tr class="skel-row">
								<td><div class="skel skel-chk" /></td>
								<td>
									<div class="skel-avatar-wrap">
										<div class="skel skel-avatar" />
										<div style="flex:1;display:flex;flex-direction:column;gap:8px;">
											<div class="skel skel-text skel-w80" />
											<div class="skel skel-text skel-w50" />
										</div>
									</div>
								</td>
								<td>
									<div class="skel skel-text skel-w95" style="margin-bottom:6px;" />
									<div class="skel skel-text skel-w70" />
								</td>
								<td><div class="skel skel-text skel-w90" /></td>
								<td><div class="skel skel-badge" /></td>
								<td><div class="skel skel-text skel-w60" /></td>
								<td>
									<div style="display:flex;gap:6px;">
										<div class="skel skel-btn" /><div class="skel skel-btn" /><div class="skel skel-btn" /><div class="skel skel-btn" />
									</div>
								</td>
							</tr>
						{/each}
					{:else if items.length === 0}
						<tr>
							<td colspan="7">
								<div class="empty-box">
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
									<div class="empty-title">暂无评论</div>
									<div class="empty-sub">当前筛选条件下没有结果</div>
								</div>
							</td>
						</tr>
					{:else}
						{#each items as c (c.id)}
							{@const s = statusFromItem(c)}
							{@const qq = "qq" in c ? c.qq : null}
							{@const gh = "github" in c ? c.github : null}
							{@const email = "author_email" in c ? c.author_email : null}
							{@const ip = "ip_address" in c ? c.ip_address : null}
							{@const parentRef = "parent_ref" in c ? c.parent_ref : null}
							{@const parent = "parent" in c ? (c as { parent?: { id?: number; nickname?: string | null } | null }).parent : null}
							{@const parentNick = parentRef?.nickname ?? parent?.nickname ?? null}
							{@const parentId = parentRef?.id ?? parent?.id ?? null}
							<tr class="data-row">
								<td>
									<label class="chk-wrap">
										<input
											type="checkbox"
											checked={selectedIds.has(c.id)}
											onchange={(e) => toggleOne(c.id, e)}
										/>
										<span class="chk-box" />
									</label>
								</td>
								<td>
									<div class="author-cell">
										{#if avatarUrl(c)}
											<img class="avatar" src={avatarUrl(c)!} alt="" referrerpolicy="no-referrer" onerror={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
										{:else}
											<div class="avatar avatar-letter" style="background:{letterBg(nicknameOf(c))};">
												{letterInitial(c)}
											</div>
										{/if}
										<div class="author-meta">
											<div class:list={["author-name", { "author-anon": isAnonymous(c) }]}>
												{nicknameOf(c)}
											</div>
											<div class="author-badges">
												{#if qq}
													<span class="mini-badge" title={`QQ: ${qq}`}>QQ</span>
												{/if}
												{#if gh}
													<span class="mini-badge" title={`GitHub: @${gh}`}>GitHub</span>
												{/if}
												{#if email}
													<span class="mini-badge mini-icon" title={email}>
														<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
													</span>
												{/if}
												{#if ip}
													<span class="mini-badge mini-icon" title={`IP: ${ip}`}>
														<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
													</span>
												{/if}
											</div>
										</div>
									</div>
								</td>
								<td>
									<div
										class="content-cell"
										class:expandable={(c.content?.length ?? 0) > 80}
										onclick={() => toggleExpand(c)}
										title={(c.content?.length ?? 0) > 80 ? "点击展开/收起" : undefined}
									>
										{#if isExpanded(c)}
											<pre class="content-full">{c.content}</pre>
										{:else}
											<span>{contentTruncated(c)}</span>
										{/if}
									</div>
									{#if parentNick || parentId}
										<div class="reply-ref">
											↩ 回复 {parentNick ?? "(已删除)"}
											{#if parentId}
												<span class="reply-id">(C{parentId})</span>
											{/if}
										</div>
									{/if}
								</td>
								<td>
									<div class="post-cell">
										<div class="post-title" title={postTitleOf(c)}>{postTitleOf(c)}</div>
										<div class="post-actions">
											<button type="button" class="link-btn" onclick={() => previewPost(c)}>预览</button>
											<span class="dot-split" />
											<button type="button" class="link-btn" onclick={() => editPost(c)}>编辑</button>
										</div>
									</div>
								</td>
								<td>
									<div
										class="status-cell"
										onmouseenter={() => (hoverStatusId = c.id)}
										onmouseleave={() => (hoverStatusId === c.id ? (hoverStatusId = null) : null)}
									>
										<span class:list={["status-badge", statusBadgeClass(s)]}>{statusLabel(s)}</span>
										{#if hoverStatusId === c.id}
											<div class="status-menu">
												<button type="button" onclick={() => runSingle("approve", c.id)}>通过</button>
												<button type="button" onclick={() => runSingle("reject", c.id, "确认拒绝该评论？")}>拒绝</button>
												<button type="button" onclick={() => runSingle("restore", c.id)}>恢复</button>
												<button type="button" onclick={() => runSingle("spam", c.id)}>标垃圾</button>
											</div>
										{/if}
									</div>
								</td>
								<td>
									<div class="time-cell">{formatDate(c.created_at)}</div>
								</td>
								<td>
									<div class="row-actions">
										<button
											type="button"
											class="btn btn-ghost btn-sm row-btn row-btn-approve"
											disabled={s === "approved"}
											onclick={() => runSingle("approve", c.id)}
											title="通过"
										>
											<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
											通过
										</button>
										<button
											type="button"
											class="btn btn-ghost btn-sm row-btn row-btn-reject"
											disabled={s === "rejected"}
											onclick={() => runSingle("reject", c.id, "确认拒绝该评论？")}
											title="拒绝"
										>
											<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
											拒绝
										</button>
										<button
											type="button"
											class="btn btn-ghost btn-sm row-btn row-btn-spam"
											disabled={s === "spam"}
											onclick={() => runSingle("spam", c.id)}
											title="标垃圾"
										>
											<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 0 0 6.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 0 0 6.001 0M18 7l-3 9m3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"/></svg>
											垃圾
										</button>
										<button
											type="button"
											class="btn btn-ghost btn-sm row-btn row-btn-del"
											onclick={() => runSingle("delete", c.id, "确认删除该评论？此操作不可恢复。")}
											title="删除"
										>
											<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
											删除
										</button>
									</div>
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>

		<!-- =============== Paginator =============== -->
		<div class="paginator">
			<div class="page-info">
				共 <b>{total}</b> 条，当前 <b>{startIdx()} ~ {endIdx()}</b>
			</div>

			<div class="page-controls">
				<div class="page-size-wrap">
					<select value={pageSize} onchange={onPageSizeSelect}>
						{#each pageSizeOptions as o}
							<option value={o}>{o} 条/页</option>
						{/each}
					</select>
				</div>

				<div class="page-buttons">
					<button
						type="button"
						class="page-btn"
						disabled={page <= 1 || loading}
						onclick={() => changePage(1)}
						title="首页"
					>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/></svg>
					</button>
					<button
						type="button"
						class="page-btn"
						disabled={page <= 1 || loading}
						onclick={() => changePage(page - 1)}
					>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
					</button>

					{#each pageRange(page, totalPages()) as p (p.key)}
						{#if p.type === "num"}
							<button
								type="button"
								class:list={["page-btn", { "page-active": p.value === page }]}
								disabled={loading}
								onclick={() => changePage(p.value as number)}
							>
								{p.value}
							</button>
						{:else if p.type === "ellipsis"}
							<span class="page-ellipsis">…</span>
						{/if}
					{/each}

					<button
						type="button"
						class="page-btn"
						disabled={page >= totalPages() || loading}
						onclick={() => changePage(page + 1)}
					>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
					</button>
					<button
						type="button"
						class="page-btn"
						disabled={page >= totalPages() || loading}
						onclick={() => changePage(totalPages())}
						title="末页"
					>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></svg>
					</button>
				</div>

				<div class="page-goto">
					跳至
					<input
						type="number"
						min="1"
						max={totalPages()}
						bind:value={pageInput}
						onkeydown={(e) => {
							if (e.key === "Enter") gotoPageInput();
						}}
					/>
					页
					<button type="button" class="btn btn-outline btn-sm" onclick={gotoPageInput}>确定</button>
				</div>
			</div>
		</div>
	</div>

	<!-- =============== Toasts =============== -->
	<div class="toast-container">
		{#each toasts as t (t.id)}
			<div class:list={["toast", `toast-${t.type}`]}>
				{#if t.type === "success"}
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
				{:else}
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
				{/if}
				<span>{t.message}</span>
			</div>
		{/each}
	</div>
</div>

<style>
	.admin-comment-list {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	/* ===== Toolbar ===== */
	.admin-toolbar {
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 14px 20px;
		background: var(--ant-bg-container);
		border: 1px solid var(--ant-border-color-secondary);
		border-radius: var(--ant-radius);
		box-shadow: var(--ant-shadow-sm);
		flex-wrap: wrap;
	}

	.filter-tabs {
		display: flex;
		align-items: center;
		gap: 4px;
		flex-wrap: wrap;
	}

	.tab-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		border: 1px solid transparent;
		background: transparent;
		border-radius: var(--ant-radius-sm);
		font-size: 13.5px;
		font-weight: 500;
		color: var(--ant-text-secondary);
		cursor: pointer;
		transition: all 0.15s ease;
		font-family: inherit;
	}
	.tab-btn:hover {
		background: var(--ant-bg-body);
		color: var(--ant-text-primary);
	}
	.tab-btn.tab-active {
		background: var(--ant-primary-bg);
		color: var(--ant-primary);
		border-color: color-mix(in srgb, var(--ant-primary) 30%, transparent);
	}

	.tab-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 20px;
		height: 18px;
		padding: 0 6px;
		font-size: 11px;
		font-weight: 600;
		border-radius: 9999px;
		background: color-mix(in srgb, currentColor 16%, transparent);
		line-height: 1;
	}

	.search-bar {
		flex: 1;
		min-width: 260px;
		max-width: 460px;
		position: relative;
		display: flex;
		align-items: center;
	}
	.search-bar svg {
		position: absolute;
		left: 10px;
		width: 15px;
		height: 15px;
		color: var(--ant-text-tertiary);
		pointer-events: none;
	}
	.search-bar input {
		width: 100%;
		padding: 7px 12px 7px 32px;
		border: 1px solid var(--ant-border-color);
		background: var(--ant-bg-container);
		border-radius: var(--ant-radius);
		font-size: 13.5px;
		color: var(--ant-text-primary);
		outline: none;
		transition: all 0.15s ease;
		font-family: inherit;
		line-height: 1.5715;
	}
	.search-bar input:focus {
		border-color: var(--ant-primary);
		box-shadow: 0 0 0 3px var(--ant-primary-bg);
	}
	.search-bar input::placeholder {
		color: var(--ant-text-tertiary);
	}

	.batch-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 10px;
		background: var(--ant-primary-bg);
		border: 1px solid color-mix(in srgb, var(--ant-primary) 28%, transparent);
		border-radius: var(--ant-radius-sm);
		opacity: 0;
		pointer-events: none;
		transform: translateY(-2px);
		transition: all 0.2s ease;
	}
	.batch-bar.visible {
		opacity: 1;
		pointer-events: auto;
		transform: translateY(0);
	}
	.batch-count {
		font-size: 12.5px;
		font-weight: 600;
		color: var(--ant-primary);
		padding: 0 4px 0 2px;
		white-space: nowrap;
	}

	/* ===== Table wrapper ===== */
	.table-wrapper {
		background: var(--ant-bg-container);
		border: 1px solid var(--ant-border-color-secondary);
		border-radius: var(--ant-radius);
		overflow: hidden;
		box-shadow: var(--ant-shadow-sm);
	}

	.table-scroll {
		overflow-x: auto;
	}

	.admin-table {
		width: 100%;
		border-collapse: separate;
		border-spacing: 0;
		min-width: 1100px;
	}

	.admin-table th {
		text-align: left;
		padding: 12px 16px;
		font-size: 13px;
		font-weight: 600;
		color: var(--ant-text-secondary);
		background: var(--ant-bg-body);
		white-space: nowrap;
		border-bottom: 1px solid var(--ant-border-split);
		line-height: 1.5;
		position: sticky;
		top: 0;
		z-index: 1;
	}
	.admin-table th:first-child {
		padding-left: 20px;
	}
	.admin-table th:last-child {
		padding-right: 20px;
	}

	.admin-table td {
		padding: 14px 16px;
		font-size: 13.5px;
		color: var(--ant-text-primary);
		vertical-align: top;
		border-bottom: 1px solid var(--ant-border-split);
		line-height: 1.55;
	}
	.admin-table td:first-child {
		padding-left: 20px;
		vertical-align: middle;
	}
	.admin-table td:last-child {
		padding-right: 20px;
	}
	.admin-table tbody tr:last-child td {
		border-bottom: none;
	}
	.admin-table tbody tr.data-row:hover {
		background: color-mix(in srgb, var(--ant-primary) 4%, transparent);
	}

	/* ===== Checkbox ===== */
	.chk-wrap {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		position: relative;
		cursor: pointer;
		width: 18px;
		height: 18px;
	}
	.chk-wrap input[type="checkbox"] {
		opacity: 0;
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		cursor: pointer;
		z-index: 2;
		margin: 0;
	}
	.chk-box {
		width: 18px;
		height: 18px;
		border: 1.5px solid var(--ant-border-color);
		border-radius: 5px;
		background: var(--ant-bg-container);
		transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.chk-wrap input:checked + .chk-box {
		background: var(--ant-primary);
		border-color: var(--ant-primary);
	}
	.chk-wrap input:checked + .chk-box::after {
		content: "";
		width: 5px;
		height: 9px;
		border: solid #fff;
		border-width: 0 2px 2px 0;
		transform: rotate(45deg) translate(-1px, -1px);
	}
	.chk-wrap input:indeterminate + .chk-box {
		background: var(--ant-primary);
		border-color: var(--ant-primary);
	}
	.chk-wrap input:indeterminate + .chk-box::after {
		content: "";
		width: 10px;
		height: 2px;
		background: #fff;
		border-radius: 1px;
	}
	.chk-wrap:hover .chk-box {
		border-color: var(--ant-primary);
	}
	.chk-wrap input:focus + .chk-box {
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--ant-primary) 18%, transparent);
		border-color: var(--ant-primary);
	}

	/* ===== Author cell ===== */
	.author-cell {
		display: flex;
		align-items: center;
		gap: 12px;
		min-width: 0;
	}
	.avatar {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		object-fit: cover;
		flex-shrink: 0;
		background: var(--ant-bg-body);
		border: 1px solid var(--ant-border-color-secondary);
	}
	.avatar-letter {
		display: flex;
		align-items: center;
		justify-content: center;
		color: #fff;
		font-weight: 600;
		font-size: 14px;
		border: none;
	}
	.author-meta {
		min-width: 0;
		flex: 1;
	}
	.author-name {
		font-size: 13.5px;
		font-weight: 600;
		color: var(--ant-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		line-height: 1.3;
	}
	.author-name.author-anon {
		color: var(--ant-text-tertiary);
		font-style: italic;
		font-weight: 500;
	}
	.author-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 4px;
	}
	.mini-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 1px 6px;
		font-size: 10.5px;
		font-weight: 600;
		border-radius: 4px;
		background: var(--ant-bg-body);
		color: var(--ant-text-secondary);
		line-height: 1.5;
		letter-spacing: 0.01em;
	}
	.mini-badge.mini-icon {
		width: 20px;
		height: 18px;
		padding: 0;
	}
	.mini-badge.mini-icon svg {
		width: 11px;
		height: 11px;
	}

	/* ===== Content cell ===== */
	.content-cell {
		font-size: 13.5px;
		line-height: 1.6;
		color: var(--ant-text-primary);
		word-break: break-word;
		white-space: pre-wrap;
	}
	.content-cell.expandable {
		cursor: pointer;
	}
	.content-full {
		margin: 0;
		font-family: inherit;
		font-size: inherit;
		line-height: inherit;
		color: inherit;
		white-space: pre-wrap;
		word-break: break-word;
		background: var(--ant-bg-body);
		padding: 8px 10px;
		border-radius: var(--ant-radius-sm);
		border: 1px dashed var(--ant-border-color-secondary);
	}
	.reply-ref {
		margin-top: 6px;
		font-size: 12px;
		color: var(--ant-text-tertiary);
		line-height: 1.4;
	}
	.reply-id {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 11.5px;
		opacity: 0.8;
	}

	/* ===== Post cell ===== */
	.post-cell {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.post-title {
		font-size: 13.5px;
		font-weight: 500;
		color: var(--ant-text-primary);
		line-height: 1.4;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.post-actions {
		display: flex;
		align-items: center;
		gap: 0;
		flex-wrap: wrap;
	}
	.link-btn {
		display: inline-flex;
		align-items: center;
		padding: 2px 4px;
		border: none;
		background: transparent;
		font-size: 12px;
		color: var(--ant-primary);
		cursor: pointer;
		font-family: inherit;
		line-height: 1.4;
		border-radius: 3px;
		transition: background 0.15s;
	}
	.link-btn:hover {
		background: var(--ant-primary-bg);
	}
	.dot-split {
		width: 1px;
		height: 10px;
		background: var(--ant-border-color-secondary);
		margin: 0 2px;
		align-self: center;
	}

	/* ===== Status cell ===== */
	.status-cell {
		position: relative;
		display: inline-flex;
		align-items: center;
	}
	.status-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 3px 10px;
		font-size: 12px;
		font-weight: 600;
		border-radius: 9999px;
		line-height: 1.4;
		letter-spacing: 0.01em;
	}
	.status-badge.badge-pending {
		background: #fff7e6;
		color: #d46b08;
		border: 1px solid #ffd591;
	}
	html.dark .status-badge.badge-pending {
		background: color-mix(in srgb, #fa8c16 18%, transparent);
		color: #ffc069;
		border-color: color-mix(in srgb, #fa8c16 35%, transparent);
	}
	.status-badge.badge-approved {
		background: #f6ffed;
		color: #389e0d;
		border: 1px solid #b7eb8f;
	}
	html.dark .status-badge.badge-approved {
		background: color-mix(in srgb, #52c41a 18%, transparent);
		color: #95de64;
		border-color: color-mix(in srgb, #52c41a 35%, transparent);
	}
	.status-badge.badge-rejected {
		background: #fff1f0;
		color: #cf1322;
		border: 1px solid #ffa39e;
	}
	html.dark .status-badge.badge-rejected {
		background: color-mix(in srgb, #ff4d4f 18%, transparent);
		color: #ff7875;
		border-color: color-mix(in srgb, #ff4d4f 35%, transparent);
	}
	.status-badge.badge-spam {
		background: #fafafa;
		color: #595959;
		border: 1px solid #d9d9d9;
	}
	html.dark .status-badge.badge-spam {
		background: color-mix(in srgb, #8c8c8c 18%, transparent);
		color: #bfbfbf;
		border-color: color-mix(in srgb, #8c8c8c 35%, transparent);
	}

	.status-menu {
		position: absolute;
		top: calc(100% + 6px);
		left: 0;
		z-index: 20;
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 4px;
		background: var(--ant-bg-container);
		border: 1px solid var(--ant-border-color-secondary);
		border-radius: var(--ant-radius);
		box-shadow: var(--ant-shadow-lg);
		min-width: 110px;
		animation: fadeIn 0.12s ease-out;
	}
	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(-3px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.status-menu button {
		display: flex;
		align-items: center;
		padding: 6px 10px;
		border: none;
		background: transparent;
		border-radius: var(--ant-radius-sm);
		font-size: 12.5px;
		color: var(--ant-text-secondary);
		cursor: pointer;
		font-family: inherit;
		text-align: left;
		line-height: 1.4;
		transition: all 0.12s;
	}
	.status-menu button:hover {
		background: var(--ant-bg-body);
		color: var(--ant-text-primary);
	}

	/* ===== Time cell ===== */
	.time-cell {
		font-size: 12.5px;
		color: var(--ant-text-secondary);
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		line-height: 1.5;
		white-space: nowrap;
	}

	/* ===== Row actions ===== */
	.row-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		align-items: center;
	}
	.row-btn {
		gap: 3px;
	}
	.row-btn svg {
		width: 12px;
		height: 12px;
	}
	.row-btn-approve:not(:disabled) {
		color: var(--admin-success);
	}
	.row-btn-approve:not(:disabled):hover {
		background: color-mix(in srgb, var(--sage-500) 12%, transparent);
	}
	.row-btn-reject:not(:disabled) {
		color: var(--ant-text-secondary);
	}
	.row-btn-reject:not(:disabled):hover {
		background: color-mix(in srgb, #fa8c16 12%, transparent);
		color: #d46b08;
	}
	.row-btn-spam:not(:disabled) {
		color: var(--ant-text-secondary);
	}
	.row-btn-spam:not(:disabled):hover {
		background: color-mix(in srgb, #8c8c8c 14%, transparent);
		color: var(--ant-text-primary);
	}
	.row-btn-del:not(:disabled) {
		color: var(--admin-error);
	}
	.row-btn-del:not(:disabled):hover {
		background: color-mix(in srgb, #ff4d4f 12%, transparent);
	}

	/* ===== Skeleton ===== */
	.skel {
		background: linear-gradient(
			90deg,
			color-mix(in srgb, var(--ant-border-color-secondary) 60%, transparent) 0%,
			color-mix(in srgb, var(--ant-border-color-secondary) 90%, transparent) 50%,
			color-mix(in srgb, var(--ant-border-color-secondary) 60%, transparent) 100%
		);
		background-size: 200% 100%;
		animation: skel 1.3s ease-in-out infinite;
		border-radius: 4px;
	}
	@keyframes skel {
		0% { background-position: 200% 0; }
		100% { background-position: -200% 0; }
	}
	.skel-chk { width: 18px; height: 18px; border-radius: 5px; }
	.skel-avatar {
		width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
	}
	.skel-avatar-wrap {
		display: flex; align-items: center; gap: 12px;
	}
	.skel-text { height: 14px; }
	.skel-w50 { width: 50%; }
	.skel-w60 { width: 60%; }
	.skel-w70 { width: 70%; }
	.skel-w80 { width: 80%; }
	.skel-w90 { width: 90%; }
	.skel-w95 { width: 95%; }
	.skel-badge { width: 58px; height: 22px; border-radius: 9999px; }
	.skel-btn { width: 42px; height: 28px; border-radius: var(--ant-radius-sm); }

	/* ===== Error / Empty ===== */
	.error-box {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		padding: 56px 20px;
		color: var(--admin-error);
		cursor: pointer;
		user-select: none;
		transition: background 0.15s;
		border-radius: 6px;
	}
	.error-box:hover {
		background: color-mix(in srgb, #ff4d4f 5%, transparent);
	}
	.error-box svg {
		width: 38px; height: 38px; opacity: 0.7;
	}
	.error-msg {
		font-size: 15px; font-weight: 600; color: var(--ant-text-primary);
	}
	.error-sub {
		font-size: 12.5px; color: var(--ant-text-tertiary);
	}

	.empty-box {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		padding: 56px 20px;
		color: var(--ant-text-tertiary);
	}
	.empty-box svg {
		width: 42px; height: 42px; opacity: 0.5;
	}
	.empty-title {
		font-size: 15px; font-weight: 600; color: var(--ant-text-secondary);
	}
	.empty-sub {
		font-size: 12.5px; color: var(--ant-text-quaternary);
	}

	/* ===== Paginator ===== */
	.paginator {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 14px 20px;
		border-top: 1px solid var(--ant-border-split);
		flex-wrap: wrap;
	}
	.page-info {
		font-size: 13px;
		color: var(--ant-text-secondary);
		line-height: 1.5;
	}
	.page-info b {
		color: var(--ant-text-primary);
		font-weight: 600;
	}

	.page-controls {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}

	.page-size-wrap select {
		padding: 4px 28px 4px 10px;
		border: 1px solid var(--ant-border-color);
		background: var(--ant-bg-container);
		border-radius: var(--ant-radius-sm);
		font-size: 13px;
		color: var(--ant-text-primary);
		outline: none;
		cursor: pointer;
		font-family: inherit;
		line-height: 1.5;
		height: 30px;
		appearance: none;
		background-image: linear-gradient(45deg, transparent 50%, var(--ant-text-tertiary) 50%),
			linear-gradient(135deg, var(--ant-text-tertiary) 50%, transparent 50%);
		background-position: calc(100% - 14px) 50%, calc(100% - 10px) 50%;
		background-size: 4px 4px, 4px 4px;
		background-repeat: no-repeat;
		transition: border-color 0.15s;
	}
	.page-size-wrap select:hover,
	.page-size-wrap select:focus {
		border-color: var(--ant-primary);
	}

	.page-buttons {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.page-btn {
		min-width: 30px;
		height: 30px;
		padding: 0 8px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--ant-border-color);
		background: var(--ant-bg-container);
		border-radius: var(--ant-radius-sm);
		font-size: 13px;
		color: var(--ant-text-secondary);
		cursor: pointer;
		font-family: inherit;
		line-height: 1;
		transition: all 0.15s;
	}
	.page-btn svg {
		width: 13px;
		height: 13px;
	}
	.page-btn:hover:not(:disabled) {
		border-color: var(--ant-primary);
		color: var(--ant-primary);
	}
	.page-btn.page-active {
		background: var(--ant-primary);
		border-color: var(--ant-primary);
		color: #fff;
		font-weight: 600;
	}
	.page-btn.page-active:hover {
		color: #fff;
	}
	.page-btn:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
	.page-ellipsis {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 30px;
		height: 30px;
		color: var(--ant-text-quaternary);
		font-size: 14px;
	}

	.page-goto {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: var(--ant-text-secondary);
		line-height: 1.5;
	}
	.page-goto input {
		width: 56px;
		height: 30px;
		padding: 4px 8px;
		border: 1px solid var(--ant-border-color);
		background: var(--ant-bg-container);
		border-radius: var(--ant-radius-sm);
		font-size: 13px;
		color: var(--ant-text-primary);
		outline: none;
		font-family: inherit;
		line-height: 1.5;
		text-align: center;
		transition: border-color 0.15s;
	}
	.page-goto input:focus {
		border-color: var(--ant-primary);
		box-shadow: 0 0 0 2px var(--ant-primary-bg);
	}

	/* ===== Toasts ===== */
	.toast-container {
		position: fixed;
		top: 80px;
		right: 24px;
		z-index: 9999;
		display: flex;
		flex-direction: column;
		gap: 10px;
		pointer-events: none;
	}
	.toast {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 10px 16px;
		border-radius: var(--ant-radius);
		box-shadow: var(--ant-shadow-lg);
		font-size: 13.5px;
		font-weight: 500;
		line-height: 1.4;
		min-width: 200px;
		max-width: 380px;
		pointer-events: auto;
		animation: toastIn 0.25s cubic-bezier(0.22, 1, 0.36, 1);
		backdrop-filter: blur(6px);
	}
	@keyframes toastIn {
		from { opacity: 0; transform: translateX(18px) scale(0.96); }
		to { opacity: 1; transform: translateX(0) scale(1); }
	}
	.toast svg {
		width: 16px; height: 16px; flex-shrink: 0;
	}
	.toast-success {
		background: color-mix(in srgb, #f6ffed 92%, transparent);
		border: 1px solid #b7eb8f;
		color: #389e0d;
	}
	html.dark .toast-success {
		background: color-mix(in srgb, #52c41a 22%, rgba(0,0,0,0.5));
		border-color: color-mix(in srgb, #52c41a 40%, transparent);
		color: #95de64;
	}
	.toast-error {
		background: color-mix(in srgb, #fff1f0 92%, transparent);
		border: 1px solid #ffa39e;
		color: #cf1322;
	}
	html.dark .toast-error {
		background: color-mix(in srgb, #ff4d4f 22%, rgba(0,0,0,0.5));
		border-color: color-mix(in srgb, #ff4d4f 40%, transparent);
		color: #ffa39e;
	}

	/* ===== Utility btn (extend) ===== */
	.btn-success {
		background: var(--admin-success);
		color: #fff;
		border-color: var(--admin-success);
	}
	.btn-success:hover:not(:disabled) {
		filter: brightness(1.08);
		border-color: var(--admin-success);
	}
</style>
