<script lang="ts">
import { createEventDispatcher, onMount } from "svelte";
import {
	activateUser,
	banUser,
	deleteUser,
	getUsers,
	resetUserPassword,
	unbanUser,
} from "@/api/admin";
import type {
	AdminUserListParams,
	PaginatedResponse,
	UserDetailResponse,
} from "@/api/schema-contract";
import AdminUserDetailDrawer from "./AdminUserDetailDrawer.svelte";

const dispatch = createEventDispatcher<{
	saved: number;
}>();

type FilterKey = "all" | "staff" | "active" | "inactive" | "banned";

const FILTER_TABS: { key: FilterKey; label: string }[] = [
	{ key: "all", label: "全部" },
	{ key: "staff", label: "员工" },
	{ key: "active", label: "激活" },
	{ key: "inactive", label: "禁用" },
	{ key: "banned", label: "封禁" },
];

const PAGE_SIZE_OPTIONS = [10, 20, 50];
const AVATAR_COLORS = [
	"#f56c6c",
	"#e6a23c",
	"#67c23a",
	"#409eff",
	"#909399",
	"#8e44ad",
	"#16a085",
	"#d35400",
	"#2980b9",
	"#c0392b",
	"#27ae60",
	"#f39c12",
];

let loading = false;
let users: UserDetailResponse[] = [];
let total = 0;
let page = 1;
let page_size = 20;
let search = "";
let searchDebounce: number | null = null;
let activeFilter: FilterKey = "all";
let selectedIds: Set<number> = new Set();
let drawerUserId: number | null = null;
let drawerOpen = false;

let modalType: "delete" | "reset-password" | null = null;
let modalTarget: UserDetailResponse | null = null;
let modalLoading = false;
let newPassword = "";
let newPasswordConfirm = "";
let deleteConfirmText = "";

function getAvatarColor(seed: string): string {
	let hash = 0;
	for (let i = 0; i < seed.length; i++) {
		hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
	}
	return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

function getAvatarUrl(u: UserDetailResponse, size = 40): string {
	if (u.resolved_avatar_url) {
		const src = encodeURIComponent(u.resolved_avatar_url);
		return `/api/avatar/by-url?src=${src}&size=${size}`;
	}
	return "";
}

function getInitial(u: UserDetailResponse): string {
	const name = u.nickname || u.username || "?";
	return name.trim().charAt(0).toUpperCase();
}

function getRoleBadge(u: UserDetailResponse): { label: string; cls: string } {
	if (u.is_superuser) return { label: "超级管理员", cls: "badge-error" };
	if (u.is_staff) return { label: "员工", cls: "badge-warning" };
	return { label: "订阅者", cls: "badge-ghost" };
}

function getStatusBadges(
	u: UserDetailResponse,
): { label: string; cls: string; solid?: boolean }[] {
	const badges: { label: string; cls: string; solid?: boolean }[] = [];
	if (u.is_banned) {
		badges.push({ label: "已封禁", cls: "badge-error", solid: true });
	} else if (u.is_active) {
		badges.push({ label: "已激活", cls: "badge-success" });
	} else {
		badges.push({ label: "未激活", cls: "badge-ghost" });
	}
	return badges;
}

function formatDate(s: string | null | undefined): string {
	if (!s) return "-";
	const d = new Date(s);
	if (Number.isNaN(d.getTime())) return "-";
	return (
		d.toLocaleDateString("zh-CN") +
		" " +
		d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
	);
}

function showToast(msg: string, type: "success" | "error" | "info" = "info") {
	const w = window as unknown as {
		showToast?: (m: string, t?: string) => void;
	};
	if (w.showToast) {
		w.showToast(msg, type);
	} else {
		const el = document.createElement("div");
		el.className = "toast-container";
		el.textContent = msg;
		el.style.cssText = `
				position:fixed;top:80px;left:50%;transform:translateX(-50%) translateY(-12px);
				background:hsl(var(--bc));color:#fff;padding:10px 20px;border-radius:8px;z-index:9999;
				opacity:0;transition:all .25s;font-size:14px;box-shadow:0 6px 20px rgba(0,0,0,.15);
			`;
		document.body.appendChild(el);
		requestAnimationFrame(() => {
			el.style.opacity = "1";
			el.style.transform = "translateX(-50%) translateY(0)";
		});
		setTimeout(() => {
			el.style.opacity = "0";
			setTimeout(() => el.remove(), 250);
		}, 2000);
	}
}

function buildParams(): AdminUserListParams {
	const p: AdminUserListParams = {
		page,
		page_size,
		search: search.trim() || undefined,
	};
	switch (activeFilter) {
		case "staff":
			p.is_staff = true;
			break;
		case "active":
			p.is_active = true;
			p.is_banned = false;
			break;
		case "inactive":
			p.is_active = false;
			p.is_banned = false;
			break;
		case "banned":
			p.is_banned = true;
			break;
	}
	return p;
}

async function loadData() {
	loading = true;
	try {
		const res: PaginatedResponse<UserDetailResponse> = await getUsers(
			buildParams(),
		);
		users = res.items || [];
		total = res.total || 0;
		if (res.page && res.page !== page) page = res.page;
	} catch (e) {
		showToast("加载失败，请刷新重试", "error");
		console.error(e);
		users = [];
		total = 0;
	} finally {
		loading = false;
	}
}

$: if (page || page_size || activeFilter) {
	// reactive load on page/filter/size change
}

function onSearchInput(ev: Event) {
	const v = (ev.target as HTMLInputElement).value;
	if (searchDebounce) window.clearTimeout(searchDebounce);
	searchDebounce = window.setTimeout(() => {
		search = v;
		page = 1;
		loadData();
	}, 300);
}

function onFilterChange(key: FilterKey) {
	if (activeFilter === key) return;
	activeFilter = key;
	page = 1;
	selectedIds.clear();
	loadData();
}

function onPageChange(p: number) {
	const totalPages = Math.max(1, Math.ceil(total / page_size));
	if (p < 1 || p > totalPages) return;
	page = p;
	loadData();
}

function onPageSizeChange(ev: Event) {
	const s = Number((ev.target as HTMLSelectElement).value);
	if (!PAGE_SIZE_OPTIONS.includes(s)) return;
	page_size = s;
	page = 1;
	loadData();
}

function toggleSelectAll(ev: Event) {
	const checked = (ev.target as HTMLInputElement).checked;
	if (checked) {
		for (const u of users) selectedIds.add(u.id);
	} else {
		selectedIds.clear();
	}
	selectedIds = new Set(selectedIds);
}

function toggleSelectRow(id: number, ev: Event) {
	ev.stopPropagation();
	if (selectedIds.has(id)) selectedIds.delete(id);
	else selectedIds.add(id);
	selectedIds = new Set(selectedIds);
}

function openDrawer(id: number) {
	drawerUserId = id;
	drawerOpen = true;
}

function closeDrawer() {
	drawerOpen = false;
}

function onRowClick(u: UserDetailResponse, ev: MouseEvent) {
	const t = ev.target as HTMLElement;
	if (t.closest(".row-action, .row-checkbox, a, button, input[type=checkbox]"))
		return;
	openDrawer(u.id);
}

async function onToggleStatus(u: UserDetailResponse, ev: MouseEvent) {
	ev.stopPropagation();
	try {
		if (u.is_banned) {
			await unbanUser(u.id);
			showToast("已解除封禁", "success");
		} else if (!u.is_active) {
			await activateUser(u.id);
			showToast("已激活用户", "success");
		} else {
			await banUser(u.id);
			showToast("已封禁用户", "success");
		}
		loadData();
	} catch (e) {
		showToast("操作失败", "error");
		console.error(e);
	}
}

function openResetPassword(u: UserDetailResponse, ev: MouseEvent) {
	ev.stopPropagation();
	modalType = "reset-password";
	modalTarget = u;
	newPassword = "";
	newPasswordConfirm = "";
	modalLoading = false;
}

function openDelete(u: UserDetailResponse, ev: MouseEvent) {
	ev.stopPropagation();
	modalType = "delete";
	modalTarget = u;
	deleteConfirmText = "";
	modalLoading = false;
}

function closeModal() {
	if (modalLoading) return;
	modalType = null;
	modalTarget = null;
}

function validatePassword(p: string): { ok: boolean; msg: string } {
	if (p.length < 8) return { ok: false, msg: "至少 8 位" };
	if (!/[A-Za-z]/.test(p)) return { ok: false, msg: "必须包含字母" };
	if (!/\d/.test(p)) return { ok: false, msg: "必须包含数字" };
	return { ok: true, msg: "" };
}

$: passwordValidation = validatePassword(newPassword);
declare let passwordValidation: { ok: boolean; msg: string };
$: passwordMatch = newPassword === newPasswordConfirm;
declare let passwordMatch: boolean;

async function confirmResetPassword() {
	if (!modalTarget) return;
	const v = validatePassword(newPassword);
	if (!v.ok) {
		showToast(`密码强度不足：${v.msg}`, "error");
		return;
	}
	if (!passwordMatch) {
		showToast("两次密码不一致", "error");
		return;
	}
	modalLoading = true;
	try {
		await resetUserPassword(modalTarget.id, { new_password: newPassword });
		showToast("密码已重置", "success");
		closeModal();
	} catch (e) {
		showToast("重置失败", "error");
		console.error(e);
	} finally {
		modalLoading = false;
	}
}

async function confirmDelete() {
	if (!modalTarget) return;
	if (deleteConfirmText !== "DELETE") {
		showToast('请输入 "DELETE" 确认', "error");
		return;
	}
	modalLoading = true;
	try {
		await deleteUser(modalTarget.id);
		showToast("已删除用户", "success");
		closeModal();
		loadData();
	} catch (e) {
		showToast("删除失败", "error");
		console.error(e);
	} finally {
		modalLoading = false;
	}
}

function onDrawerSaved() {
	loadData();
	dispatch("saved", drawerUserId ?? 0);
}

$: totalPages = Math.max(1, Math.ceil(total / page_size));
declare let totalPages: number;
$: allSelected = users.length > 0 && users.every((u) => selectedIds.has(u.id));
declare let allSelected: boolean;
$: displayStart = total === 0 ? 0 : (page - 1) * page_size + 1;
declare let displayStart: number;
$: displayEnd = Math.min(page * page_size, total);
declare let displayEnd: number;

onMount(() => {
	loadData();
});
</script>

<!-- ============================================================= -->

<div class="admin-table-wrapper">
	<div class="admin-table-header">
		<div style="display:flex;align-items:center;gap:14px;">
			<h3 class="admin-table-title">所有用户</h3>
			<span class="badge badge-ghost">{total} 位</span>
		</div>
		<div class="admin-table-actions">
			<div class="search-bar">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
				</svg>
				<input
					type="text"
					class="admin-input admin-input-sm"
					placeholder="搜索昵称/用户名/邮箱..."
					on:input={onSearchInput}
					value={search}
				/>
			</div>
		</div>
	</div>

	<div class="filter-tabs">
		{#each FILTER_TABS as t (t.key)}
			<button
				class="filter-tab {activeFilter === t.key ? 'active' : ''}"
				on:click={() => onFilterChange(t.key)}
				type="button"
			>{t.label}</button>
		{/each}
	</div>

	<div class="admin-table-scroll">
		<table class="admin-table">
			<thead>
				<tr>
					<th style="width:44px;padding-left:24px;">
						<label class="admin-checkbox-wrapper" title="全选">
							<input type="checkbox" class="admin-checkbox" on:change={toggleSelectAll} checked={allSelected}/>
							<span class="admin-checkmark"></span>
						</label>
					</th>
					<th>用户</th>
					<th>邮箱</th>
					<th>角色</th>
					<th style="text-align:center;">文章/评论</th>
					<th>注册时间</th>
					<th>状态</th>
					<th style="width:260px;padding-right:24px;">操作</th>
				</tr>
			</thead>
			<tbody>
				{#if loading}
					<tr>
						<td colspan="8" class="admin-empty-cell">
							<div class="admin-empty">
								<div class="admin-empty-icon">
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
										<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
									</svg>
								</div>
								<div class="admin-empty-title">加载中...</div>
							</div>
						</td>
					</tr>
				{:else if users.length === 0}
					<tr>
						<td colspan="8" class="admin-empty-cell">
							<div class="admin-empty">
								<div class="admin-empty-icon">
									<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
										<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
										<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
									</svg>
								</div>
								<div class="admin-empty-title">暂无用户</div>
								<div class="admin-empty-desc">还没有注册用户</div>
							</div>
						</td>
					</tr>
				{:else}
					{#each users as u (u.id)}
						<tr class="admin-table-row" on:click={(e) => onRowClick(u, e)}>
							<td style="padding-left:24px;">
								<label class="admin-checkbox-wrapper row-checkbox" on:click|stopPropagation={() => {}}>
									<input type="checkbox" class="admin-checkbox" checked={selectedIds.has(u.id)} on:change={(e) => toggleSelectRow(u.id, e)}/>
									<span class="admin-checkmark"></span>
								</label>
							</td>
							<td>
								<div class="user-cell">
									{#if getAvatarUrl(u)}
										<img src={getAvatarUrl(u, 80)} alt="" class="user-avatar" loading="lazy"/>
									{:else}
										<div class="user-avatar user-avatar-letter" style="background:{getAvatarColor(u.username || String(u.id))};">{getInitial(u)}</div>
									{/if}
									<div class="user-meta">
										<div class="user-nickname">{u.nickname || u.username}</div>
										<div class="user-username">@{u.username}</div>
									</div>
								</div>
							</td>
							<td><span class="admin-email">{u.email || "-"}</span></td>
							<td>
								<span class="badge {getRoleBadge(u).cls}">{getRoleBadge(u).label}</span>
							</td>
							<td style="text-align:center;">
								<div style="display:inline-flex;gap:4px;align-items:center;justify-content:center;">
									<span class="badge badge-info" title="文章数">{u.posts_count ?? 0}</span>
									<span class="badge badge-secondary" title="评论数">{u.comments_count ?? 0}</span>
								</div>
							</td>
							<td class="admin-date">{formatDate(u.created_at)}</td>
							<td>
								<div style="display:flex;gap:4px;flex-wrap:wrap;">
									{#each getStatusBadges(u) as b (b.label)}
										<span class="badge {b.cls}" class:badge-solid-solid={b.solid}>{b.label}</span>
									{/each}
								</div>
							</td>
							<td style="padding-right:24px;">
								<div class="action-buttons row-action">
									<button class="btn btn-ghost btn-icon btn-sm" title="查看/编辑" on:click|stopPropagation={() => openDrawer(u.id)} type="button">
										<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
											<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
											<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
										</svg>
									</button>
									<button
										class="btn btn-ghost btn-icon btn-sm"
										title={u.is_banned ? "解除封禁" : (u.is_active ? "封禁用户" : "激活用户")}
										on:click={(e) => onToggleStatus(u, e)}
										type="button"
										style={u.is_banned ? "color:#16a34a;" : (!u.is_active ? "color:#16a34a;" : "color:#ef4444;")}
									>
										{#if u.is_banned}
											<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
												<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
											</svg>
										{:else if !u.is_active}
											<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
												<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
											</svg>
										{:else}
											<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
												<circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
											</svg>
										{/if}
									</button>
									<button class="btn btn-ghost btn-icon btn-sm" title="重置密码" on:click={(e) => openResetPassword(u, e)} type="button">
										<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
											<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
											<path d="M7 11V7a5 5 0 0 1 10 0v4"/>
										</svg>
									</button>
									<button class="btn btn-ghost btn-icon btn-sm" title="删除" style="color:hsl(var(--er));" on:click={(e) => openDelete(u, e)} type="button">
										<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
											<polyline points="3 6 5 6 21 6"/>
											<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
										</svg>
									</button>
								</div>
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>

	<div class="paginator">
		<span class="pagination-info">显示 {displayStart} ~ {displayEnd} / {total}</span>
		<div style="display:flex;align-items:center;gap:12px;">
			<select class="admin-select admin-select-sm paginator-size" on:change={onPageSizeChange} value={page_size}>
				{#each PAGE_SIZE_OPTIONS as s (s)}
					<option value={s}>{s} 条/页</option>
				{/each}
			</select>
			<div class="pagination-buttons">
				<button class="page-btn" disabled={page <= 1} on:click={() => onPageChange(page - 1)} type="button">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
				</button>

				{#if totalPages <= 7}
					{#each Array.from({ length: totalPages }, (_, i) => i + 1) as i (i)}
						<button class="page-btn {page === i ? 'active' : ''}" on:click={() => onPageChange(i)} type="button">{i}</button>
					{/each}
				{:else}
					<button class="page-btn {page === 1 ? 'active' : ''}" on:click={() => onPageChange(1)} type="button">1</button>
					{#if page > 3}
						<span class="page-btn page-ellipsis">...</span>
					{/if}
					{#each Array.from({ length: 3 }, (_, i) => Math.max(2, Math.min(totalPages - 2, page - 1)) + i) as i (i)}
						{#if i > 1 && i < totalPages}
							<button class="page-btn {page === i ? 'active' : ''}" on:click={() => onPageChange(i)} type="button">{i}</button>
						{/if}
					{/each}
					{#if page < totalPages - 2}
						<span class="page-btn page-ellipsis">...</span>
					{/if}
					<button class="page-btn {page === totalPages ? 'active' : ''}" on:click={() => onPageChange(totalPages)} type="button">{totalPages}</button>
				{/if}

				<button class="page-btn" disabled={page >= totalPages} on:click={() => onPageChange(page + 1)} type="button">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
				</button>
			</div>
		</div>
	</div>
</div>

<!-- ===== Drawer ===== -->
<AdminUserDetailDrawer
	open={drawerOpen}
	userId={drawerUserId}
	on:close={closeDrawer}
	on:saved={onDrawerSaved}
/>

<!-- ===== Modal ===== -->
{#if modalType === "reset-password" && modalTarget}
	<div class="modal-mask open" on:click|self={closeModal} role="dialog" aria-modal="true">
		<div class="modal-card">
			<div class="admin-modal-header">
				<h3 class="admin-modal-title">重置密码 — {modalTarget.nickname || modalTarget.username}</h3>
				<button class="admin-modal-close" on:click={closeModal} type="button" disabled={modalLoading}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
					</svg>
				</button>
			</div>
			<div class="admin-modal-body">
				<div class="form-row">
					<label class="form-label">新密码</label>
					<input
						type="password"
						class="admin-input"
						bind:value={newPassword}
						placeholder="请输入新密码"
						disabled={modalLoading}
					/>
					<div class="form-hint" style="color:{passwordValidation.ok ? '#16a34a' : '#ef4444'};">
						{newPassword ? passwordValidation.ok ? "✓ 强度合格" : `⚠ ${passwordValidation.msg}` : "至少 8 位，且同时包含数字和字母"}
					</div>
				</div>
				<div class="form-row">
					<label class="form-label">确认密码</label>
					<input
						type="password"
						class="admin-input"
						bind:value={newPasswordConfirm}
						placeholder="再次输入新密码"
						disabled={modalLoading}
					/>
					<div class="form-hint" style="color:{!newPasswordConfirm ? '#999' : (passwordMatch ? '#16a34a' : '#ef4444')};">
						{!newPasswordConfirm ? "请再次输入密码" : passwordMatch ? "✓ 两次密码一致" : "⚠ 两次密码不一致"}
					</div>
				</div>
			</div>
			<div class="admin-modal-footer">
				<button class="btn btn-ghost btn-sm" on:click={closeModal} disabled={modalLoading} type="button">取消</button>
				<button class="btn btn-primary btn-sm" on:click={confirmResetPassword} disabled={modalLoading || !passwordValidation.ok || !passwordMatch} type="button">
					{modalLoading ? "提交中..." : "确认重置"}
				</button>
			</div>
		</div>
	</div>
{:else if modalType === "delete" && modalTarget}
	<div class="modal-mask open" on:click|self={closeModal} role="dialog" aria-modal="true">
		<div class="modal-card">
			<div class="admin-modal-header">
				<h3 class="admin-modal-title" style="color:#ef4444;">确认删除用户</h3>
				<button class="admin-modal-close" on:click={closeModal} type="button" disabled={modalLoading}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
					</svg>
				</button>
			</div>
			<div class="admin-modal-body">
				<div class="delete-warning">
					<div class="delete-warning-icon">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
							<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
						</svg>
					</div>
					<div style="min-width:0;flex:1;">
						<div style="font-weight:500;margin-bottom:6px;">确定要删除用户 <strong>{modalTarget.nickname || modalTarget.username}</strong> 吗？</div>
						<div style="font-size:13px;color:hsl(var(--bc)/0.6);line-height:1.6;">
							此操作会删除该用户的账号、关联数据，且<strong style="color:#ef4444;">不可撤销</strong>。
							请输入 <code style="background:hsl(var(--b2));padding:2px 6px;border-radius:4px;font-family:ui-monospace,monospace;">DELETE</code> 确认。
						</div>
					</div>
				</div>
				<div class="form-row" style="margin-top:16px;">
					<input
						type="text"
						class="admin-input"
						bind:value={deleteConfirmText}
						placeholder='请输入 "DELETE"'
						disabled={modalLoading}
						spellcheck="false"
						autocomplete="off"
					/>
				</div>
			</div>
			<div class="admin-modal-footer">
				<button class="btn btn-ghost btn-sm" on:click={closeModal} disabled={modalLoading} type="button">取消</button>
				<button class="btn btn-error btn-sm" on:click={confirmDelete} disabled={modalLoading || deleteConfirmText !== "DELETE"} type="button">
					{modalLoading ? "删除中..." : "确认删除"}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.search-bar {
		position: relative;
		display: inline-flex;
		align-items: center;
	}
	.search-bar svg {
		position: absolute;
		left: 12px;
		top: 50%;
		transform: translateY(-50%);
		width: 15px;
		height: 15px;
		color: hsl(var(--bc)/0.4);
		pointer-events: none;
		z-index: 1;
	}
	.search-bar input {
		padding-left: 38px;
		width: 260px;
	}

	.filter-tabs {
		display: flex;
		gap: 4px;
		padding: 10px 24px;
		border-bottom: 1px solid var(--ant-border-split);
		background: var(--ant-bg-body);
		flex-wrap: wrap;
	}
	.filter-tab {
		padding: 5px 14px;
		border-radius: 9999px;
		border: 1px solid transparent;
		background: transparent;
		color: hsl(var(--bc)/0.7);
		cursor: pointer;
		font-size: 13px;
		transition: all 0.15s;
		font-family: inherit;
	}
	.filter-tab:hover {
		background: hsl(var(--b3));
		color: hsl(var(--bc));
	}
	.filter-tab.active {
		background: var(--ant-primary-bg);
		color: var(--ant-primary);
		border-color: color-mix(in srgb, var(--ant-primary) 35%, transparent);
		font-weight: 500;
	}

	.admin-table-scroll {
		overflow-x: auto;
	}
	.admin-table {
		width: 100%;
		border-collapse: separate;
		border-spacing: 0;
		table-layout: fixed;
	}
	.admin-table thead th {
		position: sticky;
		top: 0;
		background: var(--ant-bg-body);
		z-index: 2;
		text-align: left;
		font-weight: 500;
		font-size: 13px;
		color: var(--ant-text-secondary);
		padding: 10px 14px;
		border-bottom: 1px solid var(--ant-border-split);
		white-space: nowrap;
	}
	.admin-table tbody td {
		padding: 13px 14px;
		border-bottom: 1px solid var(--ant-border-split);
		font-size: 14px;
		color: var(--ant-text-primary);
		vertical-align: middle;
	}
	.admin-table tbody tr:last-child td {
		border-bottom: none;
	}
	.admin-table-row {
		cursor: pointer;
		transition: background 0.12s;
	}
	.admin-table-row:hover {
		background: color-mix(in srgb, var(--ant-primary) 4%, transparent);
	}
	.admin-empty-cell {
		text-align: center;
		padding: 0 !important;
	}

	.admin-checkbox-wrapper {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		position: relative;
		cursor: pointer;
		width: 18px;
		height: 18px;
	}
	.admin-checkbox {
		opacity: 0;
		position: absolute;
		width: 100%;
		height: 100%;
		cursor: pointer;
		z-index: 1;
	}
	.admin-checkmark {
		width: 18px;
		height: 18px;
		border: 1.5px solid hsl(var(--b3));
		border-radius: 5px;
		background: hsl(var(--b1));
		transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.admin-checkbox:checked + .admin-checkmark {
		background: linear-gradient(135deg, var(--cyan-500), var(--cyan-600));
		border-color: transparent;
	}
	.admin-checkbox:checked + .admin-checkmark::after {
		content: '';
		width: 5px;
		height: 9px;
		border: solid white;
		border-width: 0 2px 2px 0;
		transform: rotate(45deg) translate(-1px, -1px);
	}
	.admin-checkbox:hover + .admin-checkmark {
		border-color: var(--cyan-400);
	}

	.user-cell {
		display: flex;
		align-items: center;
		gap: 12px;
		min-width: 0;
	}
	.user-avatar {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		object-fit: cover;
		flex-shrink: 0;
		border: 1px solid var(--ant-border-color-secondary);
		background: var(--ant-bg-body);
	}
	.user-avatar-letter {
		display: flex;
		align-items: center;
		justify-content: center;
		color: #fff;
		font-weight: 600;
		font-size: 15px;
		border: none;
	}
	.user-meta {
		min-width: 0;
	}
	.user-nickname {
		font-weight: 500;
		color: var(--ant-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 180px;
	}
	.user-username {
		font-size: 12px;
		color: hsl(var(--bc)/0.5);
		margin-top: 2px;
	}
	.admin-email {
		font-size: 13px;
		color: hsl(var(--bc)/0.85);
		word-break: break-all;
	}
	.admin-date {
		font-size: 12.5px;
		color: hsl(var(--bc)/0.6);
		white-space: nowrap;
	}

	.badge-solid-solid,
	:global(.badge-solid-solid) {
		background: #ef4444 !important;
		color: #fff !important;
	}

	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 6px 12px;
		border-radius: var(--ant-radius-sm);
		border: 1px solid var(--ant-border-color);
		background: hsl(var(--b1));
		color: hsl(var(--bc));
		cursor: pointer;
		font-size: 13px;
		font-weight: 400;
		transition: all 0.15s;
		font-family: inherit;
		line-height: 1.5;
		white-space: nowrap;
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.btn-ghost {
		border-color: transparent;
		background: transparent;
	}
	.btn-ghost:hover:not(:disabled) {
		background: hsl(var(--b3));
	}
	.btn-icon {
		padding: 4px;
		width: 28px;
		height: 28px;
		gap: 0;
	}
	.btn-icon svg {
		width: 15px;
		height: 15px;
	}
	.btn-sm {
		padding: 4px 10px;
		font-size: 12.5px;
		height: 28px;
	}
	.btn-primary {
		background: var(--ant-primary);
		border-color: var(--ant-primary);
		color: #fff;
	}
	.btn-primary:hover:not(:disabled) {
		filter: brightness(0.92);
	}
	.btn-error {
		background: #ef4444;
		border-color: #ef4444;
		color: #fff;
	}
	.btn-error:hover:not(:disabled) {
		filter: brightness(0.92);
	}

	.admin-input {
		width: 100%;
		height: 32px;
		padding: 4px 11px;
		border-radius: var(--ant-radius-sm);
		border: 1px solid var(--ant-border-color);
		background: hsl(var(--b1));
		color: hsl(var(--bc));
		font-size: 14px;
		font-family: inherit;
		transition: all 0.15s;
		outline: none;
		box-sizing: border-box;
		line-height: 1.5715;
	}
	.admin-input:focus {
		border-color: var(--ant-primary);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--ant-primary) 15%, transparent);
	}
	.admin-input:disabled {
		background: hsl(var(--b2));
		cursor: not-allowed;
		opacity: 0.8;
	}
	.admin-select {
		width: 100%;
		height: 32px;
		padding: 4px 36px 4px 11px;
		border-radius: var(--ant-radius-sm);
		border: 1px solid var(--ant-border-color);
		background: hsl(var(--b1));
		color: hsl(var(--bc));
		font-size: 14px;
		font-family: inherit;
		transition: all 0.15s;
		outline: none;
		box-sizing: border-box;
		cursor: pointer;
		appearance: none;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 11px center;
	}
	.admin-select:focus {
		border-color: var(--ant-primary);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--ant-primary) 15%, transparent);
	}

	.paginator {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 24px;
		gap: 16px;
		flex-wrap: wrap;
		border-top: 1px solid var(--ant-border-split);
	}
	.pagination-info {
		font-size: 14px;
		color: var(--ant-text-secondary);
	}
	.pagination-buttons {
		display: flex;
		gap: 4px;
	}
	.page-btn {
		min-width: 32px;
		height: 32px;
		padding: 0 6px;
		border: 1px solid var(--ant-border-color);
		background: var(--ant-bg-container);
		border-radius: var(--ant-radius-sm);
		font-size: 14px;
		color: var(--ant-text-primary);
		cursor: pointer;
		transition: all 0.15s;
		display: flex;
		align-items: center;
		justify-content: center;
		line-height: 1;
		font-family: inherit;
	}
	.page-btn:hover:not(:disabled) {
		color: var(--ant-primary);
		border-color: var(--ant-primary);
	}
	.page-btn.active {
		background: var(--ant-primary);
		color: #fff;
		border-color: var(--ant-primary);
	}
	.page-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.page-ellipsis {
		min-width: 32px;
		height: 32px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		color: hsl(var(--bc)/0.5);
		pointer-events: none;
	}
	.paginator-size {
		width: 110px;
		height: 28px;
	}

	/* ========= Modal ========= */
	.modal-mask {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		backdrop-filter: blur(4px);
		-webkit-backdrop-filter: blur(4px);
		z-index: 1000;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 16px;
		opacity: 0;
		visibility: hidden;
		transition: all 0.2s;
	}
	.modal-mask.open {
		opacity: 1;
		visibility: visible;
	}
	.modal-card {
		background: var(--ant-bg-container);
		border: 1px solid var(--ant-border-color-secondary);
		border-radius: var(--ant-radius-lg);
		width: 100%;
		max-width: 520px;
		max-height: 90vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		box-shadow: var(--ant-shadow-lg);
		transform: translateY(12px) scale(0.98);
		transition: transform 0.2s;
	}
	.modal-mask.open .modal-card {
		transform: translateY(0) scale(1);
	}
	.admin-modal-header {
		padding: 16px 24px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1px solid var(--ant-border-split);
	}
	.admin-modal-title {
		font-size: 16px;
		font-weight: 500;
		color: var(--ant-text-primary);
		margin: 0;
		line-height: 1.5;
	}
	.admin-modal-close {
		width: 32px;
		height: 32px;
		border: none;
		background: transparent;
		border-radius: var(--ant-radius-sm);
		cursor: pointer;
		color: var(--ant-text-tertiary);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
		flex-shrink: 0;
	}
	.admin-modal-close:hover {
		background: var(--ant-bg-body);
		color: var(--ant-text-primary);
	}
	.admin-modal-close svg { width: 16px; height: 16px; }
	.admin-modal-body {
		padding: 24px;
		overflow-y: auto;
		flex: 1;
	}
	.admin-modal-footer {
		padding: 12px 24px;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 8px;
		border-top: 1px solid var(--ant-border-split);
	}

	.form-row { margin-bottom: 14px; }
	.form-row:last-child { margin-bottom: 0; }
	.form-label {
		display: block;
		font-size: 13px;
		color: var(--ant-text-secondary);
		margin-bottom: 6px;
		font-weight: 500;
	}
	.form-hint {
		margin-top: 5px;
		font-size: 12px;
		line-height: 1.5;
	}

	.delete-warning {
		display: flex;
		gap: 14px;
		padding: 14px;
		background: #fff2f0;
		border: 1px solid #ffccc7;
		border-radius: var(--ant-radius);
	}
	:global(html.dark) .delete-warning {
		background: rgba(255, 77, 79, 0.1);
		border-color: rgba(255, 77, 79, 0.25);
	}
	.delete-warning-icon {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: #fff;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #ef4444;
		flex-shrink: 0;
	}
	:global(html.dark) .delete-warning-icon {
		background: rgba(0,0,0,0.2);
	}
	.delete-warning-icon svg { width: 22px; height: 22px; }
</style>
