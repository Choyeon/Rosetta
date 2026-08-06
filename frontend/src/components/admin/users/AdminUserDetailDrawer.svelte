<script lang="ts">
import { createEventDispatcher } from "svelte";
import {
	banUser,
	deleteUser,
	getUser,
	resetUserPassword,
	unbanUser,
	updateUserFull,
} from "@/api/admin";
import type {
	AdminUserUpdateFull,
	UserDetailResponse,
} from "@/api/schema-contract";

const dispatch = createEventDispatcher<{
	close: undefined;
	saved: number;
}>();

export let userId: number | null = null;
export let open = false;

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

const AVATAR_SOURCE_OPTIONS: {
	value: NonNullable<UserDetailResponse["avatar_source"]> | "";
	label: string;
}[] = [
	{ value: "auto", label: "自动" },
	{ value: "custom", label: "自定义" },
	{ value: "github", label: "GitHub" },
	{ value: "qq", label: "QQ" },
	{ value: "gravatar", label: "Gravatar" },
];

let loading = false;
let saving = false;
let detail: UserDetailResponse | null = null;

let formNickname = "";
let formEmail = "";
let formWebsite = "";
let formGithub = "";
let formQq = "";
let formAvatarSource: NonNullable<UserDetailResponse["avatar_source"]> | "" =
	"auto";
let formAvatar = "";
let formBio = "";

let formIsActive = false;
let formIsStaff = false;
let formIsSuperuser = false;

let resetPasswordOpen = false;
let deleteOpen = false;
let modalLoading = false;

let newPwd = "";
let newPwdConfirm = "";
let deleteConfirmText = "";

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

async function loadDetail(id: number) {
	loading = true;
	detail = null;
	try {
		const d = await getUser(id);
		detail = d;
		formNickname = d.nickname ?? "";
		formEmail = d.email ?? "";
		formWebsite = d.website ?? "";
		formGithub = d.github ?? "";
		formQq = d.qq ?? "";
		formAvatarSource = d.avatar_source ?? "auto";
		formAvatar = d.avatar ?? "";
		formBio = d.bio ?? "";
		formIsActive = d.is_active;
		formIsStaff = d.is_staff;
		formIsSuperuser = d.is_superuser;
	} catch (e) {
		console.error(e);
		showToast("加载用户详情失败", "error");
	} finally {
		loading = false;
	}
}

$: if (open && userId != null) {
	loadDetail(userId);
}

$: if (formIsSuperuser) {
	formIsStaff = true;
}

function getAvatarColor(seed: string): string {
	let hash = 0;
	for (let i = 0; i < seed.length; i++) {
		hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
	}
	return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

function getAvatarUrl(size = 96): string {
	if (detail?.resolved_avatar_url) {
		const src = encodeURIComponent(detail.resolved_avatar_url);
		return `/api/avatar/by-url?src=${src}&size=${size}`;
	}
	return "";
}

function getInitial(): string {
	if (!detail) return "?";
	const name = detail.nickname || detail.username || "?";
	return name.trim().charAt(0).toUpperCase();
}

function getRoleBadge(): { label: string; cls: string } {
	if (!detail) return { label: "订阅者", cls: "badge-ghost" };
	if (detail.is_superuser) return { label: "超级管理员", cls: "badge-error" };
	if (detail.is_staff) return { label: "员工", cls: "badge-warning" };
	return { label: "订阅者", cls: "badge-ghost" };
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

function onMaskClick(e: MouseEvent) {
	if ((e.target as HTMLElement).classList.contains("drawer-mask")) {
		dispatchClose();
	}
}

function dispatchClose() {
	dispatch("close");
}

async function onSave() {
	if (!detail) return;
	saving = true;
	try {
		const payload: AdminUserUpdateFull = {
			nickname: formNickname.trim() || null,
			email: formEmail.trim() || null,
			website: formWebsite.trim() || null,
			github: formGithub.trim() || null,
			qq: formQq.trim() || null,
			avatar_source: formAvatarSource || null,
			avatar: formAvatar.trim() || null,
			bio: formBio.trim() || null,
			is_active: formIsActive,
			is_staff: formIsStaff,
			is_superuser: formIsSuperuser,
		};
		const updated = await updateUserFull(detail.id, payload);
		detail = updated;
		showToast("保存成功", "success");
		dispatch("saved", detail.id);
	} catch (e) {
		console.error(e);
		showToast("保存失败", "error");
	} finally {
		saving = false;
	}
}

async function onToggleBan() {
	if (!detail) return;
	saving = true;
	try {
		if (detail.is_banned) {
			await unbanUser(detail.id);
			showToast("已解除封禁", "success");
		} else {
			await banUser(detail.id);
			showToast("已封禁用户", "success");
		}
		detail = await getUser(detail.id);
		dispatch("saved", detail.id);
	} catch (e) {
		console.error(e);
		showToast("操作失败", "error");
	} finally {
		saving = false;
	}
}

function openResetPassword() {
	resetPasswordOpen = true;
	newPwd = "";
	newPwdConfirm = "";
	modalLoading = false;
}

function closeResetPassword() {
	if (modalLoading) return;
	resetPasswordOpen = false;
}

$: pwdValidation = (() => {
	if (newPwd.length < 8) return { ok: false, msg: "至少 8 位" };
	if (!/[A-Za-z]/.test(newPwd)) return { ok: false, msg: "必须包含字母" };
	if (!/\d/.test(newPwd)) return { ok: false, msg: "必须包含数字" };
	return { ok: true, msg: "" };
})();
declare let pwdValidation: { ok: boolean; msg: string };
$: pwdMatch = newPwd === newPwdConfirm;
declare let pwdMatch: boolean;

async function confirmResetPwd() {
	if (!detail) return;
	if (!pwdValidation.ok) {
		showToast(`密码强度不足：${pwdValidation.msg}`, "error");
		return;
	}
	if (!pwdMatch) {
		showToast("两次密码不一致", "error");
		return;
	}
	modalLoading = true;
	try {
		await resetUserPassword(detail.id, { new_password: newPwd });
		showToast("密码已重置", "success");
		closeResetPassword();
	} catch (e) {
		console.error(e);
		showToast("重置失败", "error");
	} finally {
		modalLoading = false;
	}
}

function openDelete() {
	deleteOpen = true;
	deleteConfirmText = "";
	modalLoading = false;
}

function closeDelete() {
	if (modalLoading) return;
	deleteOpen = false;
}

async function confirmDelete() {
	if (!detail) return;
	if (deleteConfirmText !== "DELETE") {
		showToast('请输入 "DELETE" 确认', "error");
		return;
	}
	modalLoading = true;
	try {
		await deleteUser(detail.id);
		showToast("已删除用户", "success");
		closeDelete();
		dispatch("saved", detail.id);
		dispatch("close");
	} catch (e) {
		console.error(e);
		showToast("删除失败", "error");
	} finally {
		modalLoading = false;
	}
}
</script>

<div
	class="drawer-mask {open ? 'open' : ''}"
	on:click={onMaskClick}
	aria-hidden={!open}
>
	<div class="drawer-panel" role="dialog" aria-modal="true" aria-label="用户详情">
		{#if loading && !detail}
			<div class="drawer-skeleton">
				<div class="drawer-skeleton-avatar"></div>
				<div class="drawer-skeleton-line w-180"></div>
				<div class="drawer-skeleton-line w-120"></div>
				<div style="height:40px;"></div>
				<div class="drawer-skeleton-line"></div>
				<div class="drawer-skeleton-line"></div>
				<div class="drawer-skeleton-line w-60"></div>
			</div>
		{:else if detail}
			<div class="drawer-inner">
				<header class="drawer-header">
					<div class="drawer-header-main">
						{#if getAvatarUrl(192)}
							<img src={getAvatarUrl(192)} alt="" class="big-avatar"/>
						{:else}
							<div class="big-avatar big-avatar-letter" style="background:{getAvatarColor(detail.username || String(detail.id))};">{getInitial()}</div>
						{/if}
						<div class="drawer-user-meta">
							<div class="drawer-user-nickname">{detail.nickname || detail.username}</div>
							<div class="drawer-user-username">@{detail.username}</div>
							<div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;">
								<span class="badge {getRoleBadge().cls}">{getRoleBadge().label}</span>
								{#if detail.is_banned}
									<span class="badge badge-error" style="background:#ef4444;color:#fff;">已封禁</span>
								{:else if detail.is_active}
									<span class="badge badge-success">已激活</span>
								{:else}
									<span class="badge badge-ghost">未激活</span>
								{/if}
							</div>
						</div>
					</div>
					<button class="drawer-close" on:click={dispatchClose} type="button" aria-label="关闭">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
						</svg>
					</button>
				</header>

				<div class="drawer-stats">
					<div class="stat-item">
						<div class="stat-num">{detail.posts_count ?? 0}</div>
						<div class="stat-label">文章</div>
					</div>
					<div class="stat-item">
						<div class="stat-num">{detail.comments_count ?? 0}</div>
						<div class="stat-label">评论</div>
					</div>
					<div class="stat-item">
						<div class="stat-num" title={formatDate(detail.created_at)}>
							{formatDate(detail.created_at).split(" ")[0]}
						</div>
						<div class="stat-label">注册</div>
					</div>
					<div class="stat-item">
						<div class="stat-num" title={detail.last_login || "-"}>
							{detail.last_login ? formatDate(detail.last_login).split(" ")[0] : "-"}
						</div>
						<div class="stat-label">最近登录</div>
					</div>
				</div>

				<div class="drawer-form">
					<section class="form-section">
						<div class="section-title">基本资料</div>

						<div class="form-grid">
							<div class="form-row">
								<label class="form-label">昵称</label>
								<input type="text" class="admin-input" bind:value={formNickname} placeholder="昵称" disabled={saving}/>
							</div>
							<div class="form-row">
								<label class="form-label">邮箱</label>
								<input type="email" class="admin-input" bind:value={formEmail} placeholder="email@example.com" disabled={saving}/>
							</div>
							<div class="form-row">
								<label class="form-label">用户名 <span class="muted">（只读）</span></label>
								<input type="text" class="admin-input" value={detail.username} disabled readonly/>
							</div>
							<div class="form-row">
								<label class="form-label">个人网站</label>
								<input type="url" class="admin-input" bind:value={formWebsite} placeholder="https://..." disabled={saving}/>
							</div>
							<div class="form-row">
								<label class="form-label">GitHub</label>
								<input type="text" class="admin-input" bind:value={formGithub} placeholder="GitHub 用户名" disabled={saving}/>
							</div>
							<div class="form-row">
								<label class="form-label">QQ</label>
								<input type="text" class="admin-input" bind:value={formQq} placeholder="QQ 号码" disabled={saving}/>
							</div>
							<div class="form-row">
								<label class="form-label">头像来源</label>
								<select class="admin-select" bind:value={formAvatarSource} disabled={saving}>
									{#each AVATAR_SOURCE_OPTIONS as opt (opt.value)}
										<option value={opt.value}>{opt.label}</option>
									{/each}
								</select>
							</div>
							<div class="form-row">
								<label class="form-label">自定义头像 URL <span class="muted">（来源为 custom 时生效）</span></label>
								<input type="url" class="admin-input" bind:value={formAvatar} placeholder="https://.../avatar.png" disabled={saving}/>
							</div>
							<div class="form-row form-row-full">
								<label class="form-label">个人简介</label>
								<textarea class="admin-input admin-textarea" bind:value={formBio} placeholder="介绍一下这位用户..." disabled={saving}></textarea>
							</div>
						</div>
					</section>

					<section class="form-section">
						<div class="section-title">权限管理</div>
						<div class="switch-list">
							<label class="switch-item">
								<div class="switch-text">
									<div class="switch-title">账号激活</div>
									<div class="switch-desc">关闭后用户无法登录</div>
								</div>
								<input type="checkbox" class="admin-toggle" bind:checked={formIsActive} disabled={saving}/>
							</label>
							<label class="switch-item">
								<div class="switch-text">
									<div class="switch-title">员工角色</div>
									<div class="switch-desc">可访问后台基础功能</div>
								</div>
								<input type="checkbox" class="admin-toggle" bind:checked={formIsStaff} disabled={saving || formIsSuperuser}/>
							</label>
							<label class="switch-item" style="border-color:color-mix(in srgb,#ef4444 35%,transparent);background:color-mix(in srgb,#ef4444 4%,transparent);">
								<div class="switch-text">
									<div class="switch-title" style="color:#ef4444;">超级管理员</div>
									<div class="switch-desc">拥有所有权限（自动启用员工角色），请谨慎授予</div>
								</div>
								<input type="checkbox" class="admin-toggle" bind:checked={formIsSuperuser} disabled={saving}/>
							</label>
						</div>
					</section>
				</div>

				<footer class="drawer-footer">
					<div class="drawer-footer-actions">
						<button class="btn btn-ghost btn-sm" on:click={openResetPassword} disabled={saving} type="button">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;">
								<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
								<path d="M7 11V7a5 5 0 0 1 10 0v4"/>
							</svg>
							重置密码
						</button>
						<button
							class="btn btn-sm {detail.is_banned ? 'btn-success' : 'btn-warning'}"
							on:click={onToggleBan}
							disabled={saving}
							type="button"
						>
							{#if detail.is_banned}
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;">
									<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
								</svg>
								解除封禁
							{:else}
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;">
									<circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
								</svg>
								封禁用户
							{/if}
						</button>
						<button class="btn btn-sm btn-error" on:click={openDelete} disabled={saving} type="button">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;">
								<polyline points="3 6 5 6 21 6"/>
								<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
							</svg>
							删除用户
						</button>
					</div>
					<div style="display:flex;gap:8px;">
						<button class="btn btn-ghost" on:click={dispatchClose} disabled={saving} type="button">取消</button>
						<button class="btn btn-primary" on:click={onSave} disabled={saving} type="button">
							{saving ? "保存中..." : "保存修改"}
						</button>
					</div>
				</footer>
			</div>
		{:else if !loading}
			<div class="drawer-empty">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width:48px;height:48px;opacity:.4;">
					<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
				</svg>
				<div style="margin-top:8px;color:hsl(var(--bc)/0.6);">无用户数据</div>
			</div>
		{/if}
	</div>
</div>

<!-- ===== Reset Password Modal ===== -->
{#if resetPasswordOpen}
	<div class="modal-mask open" on:click|self={closeResetPassword} role="dialog" aria-modal="true">
		<div class="modal-card">
			<div class="admin-modal-header">
				<h3 class="admin-modal-title">重置密码</h3>
				<button class="admin-modal-close" on:click={closeResetPassword} type="button" disabled={modalLoading}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
					</svg>
				</button>
			</div>
			<div class="admin-modal-body">
				<div class="form-row">
					<label class="form-label">新密码</label>
					<input type="password" class="admin-input" bind:value={newPwd} placeholder="请输入新密码" disabled={modalLoading}/>
					<div class="form-hint" style="color:{pwdValidation.ok ? '#16a34a' : '#ef4444'};">
						{newPwd ? pwdValidation.ok ? "✓ 强度合格" : `⚠ ${pwdValidation.msg}` : "至少 8 位，且同时包含数字和字母"}
					</div>
				</div>
				<div class="form-row">
					<label class="form-label">确认密码</label>
					<input type="password" class="admin-input" bind:value={newPwdConfirm} placeholder="再次输入新密码" disabled={modalLoading}/>
					<div class="form-hint" style="color:{!newPwdConfirm ? '#999' : (pwdMatch ? '#16a34a' : '#ef4444')};">
						{!newPwdConfirm ? "请再次输入密码" : pwdMatch ? "✓ 两次密码一致" : "⚠ 两次密码不一致"}
					</div>
				</div>
			</div>
			<div class="admin-modal-footer">
				<button class="btn btn-ghost btn-sm" on:click={closeResetPassword} disabled={modalLoading} type="button">取消</button>
				<button class="btn btn-primary btn-sm" on:click={confirmResetPwd} disabled={modalLoading || !pwdValidation.ok || !pwdMatch} type="button">
					{modalLoading ? "提交中..." : "确认重置"}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- ===== Delete Modal ===== -->
{#if deleteOpen && detail}
	<div class="modal-mask open" on:click|self={closeDelete} role="dialog" aria-modal="true">
		<div class="modal-card">
			<div class="admin-modal-header">
				<h3 class="admin-modal-title" style="color:#ef4444;">确认删除用户</h3>
				<button class="admin-modal-close" on:click={closeDelete} type="button" disabled={modalLoading}>
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
						<div style="font-weight:500;margin-bottom:6px;">确定要删除 <strong>{detail.nickname || detail.username}</strong> 吗？</div>
						<div style="font-size:13px;color:hsl(var(--bc)/0.6);line-height:1.6;">
							此操作会删除该用户账号及其关联数据，且<strong style="color:#ef4444;">不可撤销</strong>。
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
				<button class="btn btn-ghost btn-sm" on:click={closeDelete} disabled={modalLoading} type="button">取消</button>
				<button class="btn btn-error btn-sm" on:click={confirmDelete} disabled={modalLoading || deleteConfirmText !== "DELETE"} type="button">
					{modalLoading ? "删除中..." : "确认删除"}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.drawer-mask {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		backdrop-filter: blur(3px);
		-webkit-backdrop-filter: blur(3px);
		z-index: 950;
		opacity: 0;
		visibility: hidden;
		transition: opacity 0.25s, visibility 0.25s;
	}
	.drawer-mask.open {
		opacity: 1;
		visibility: visible;
	}

	.drawer-panel {
		position: absolute;
		top: 0;
		right: 0;
		width: 480px;
		max-width: 100vw;
		height: 100vh;
		background: var(--ant-bg-container);
		box-shadow: -8px 0 30px rgba(0, 0, 0, 0.15);
		transform: translateX(100%);
		transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.drawer-mask.open .drawer-panel {
		transform: translateX(0);
	}

	.drawer-inner {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}

	.drawer-skeleton {
		padding: 28px 28px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.drawer-skeleton-avatar {
		width: 92px;
		height: 92px;
		border-radius: 50%;
		background: linear-gradient(90deg, hsl(var(--b2)) 25%, hsl(var(--b3)) 50%, hsl(var(--b2)) 75%);
		background-size: 200% 100%;
		animation: skel-shimmer 1.4s infinite;
	}
	.drawer-skeleton-line {
		height: 14px;
		border-radius: 6px;
		background: linear-gradient(90deg, hsl(var(--b2)) 25%, hsl(var(--b3)) 50%, hsl(var(--b2)) 75%);
		background-size: 200% 100%;
		animation: skel-shimmer 1.4s infinite;
	}
	.w-60 { width: 60px; }
	.w-120 { width: 120px; }
	.w-180 { width: 180px; }
	@keyframes skel-shimmer {
		0% { background-position: 200% 0; }
		100% { background-position: -200% 0; }
	}

	.drawer-empty {
		padding: 48px 28px;
		display: flex;
		flex-direction: column;
		align-items: center;
		color: hsl(var(--bc)/0.5);
	}

	.drawer-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 16px;
		padding: 24px 28px 18px;
		border-bottom: 1px solid var(--ant-border-split);
		flex-shrink: 0;
	}
	.drawer-header-main {
		display: flex;
		align-items: center;
		gap: 18px;
		min-width: 0;
		flex: 1;
	}
	.big-avatar {
		width: 92px;
		height: 92px;
		border-radius: 50%;
		object-fit: cover;
		flex-shrink: 0;
		border: 3px solid var(--ant-border-color-secondary);
		background: var(--ant-bg-body);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
	}
	.big-avatar-letter {
		display: flex;
		align-items: center;
		justify-content: center;
		color: #fff;
		font-weight: 700;
		font-size: 38px;
		border: none;
	}
	.drawer-user-meta {
		min-width: 0;
		flex: 1;
	}
	.drawer-user-nickname {
		font-size: 22px;
		font-weight: 600;
		color: var(--ant-text-primary);
		line-height: 1.3;
		word-break: break-word;
	}
	.drawer-user-username {
		font-size: 13.5px;
		color: hsl(var(--bc)/0.55);
		margin-top: 2px;
	}

	.drawer-close {
		width: 34px;
		height: 34px;
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
	.drawer-close:hover {
		background: var(--ant-bg-body);
		color: var(--ant-text-primary);
	}
	.drawer-close svg { width: 18px; height: 18px; }

	.drawer-stats {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1px;
		background: var(--ant-border-split);
		border-bottom: 1px solid var(--ant-border-split);
		flex-shrink: 0;
	}
	.stat-item {
		padding: 14px 10px;
		text-align: center;
		background: var(--ant-bg-container);
	}
	.stat-num {
		font-size: 17px;
		font-weight: 600;
		color: var(--ant-text-primary);
		line-height: 1.2;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.stat-label {
		font-size: 11.5px;
		color: hsl(var(--bc)/0.55);
		margin-top: 3px;
	}

	.drawer-form {
		flex: 1;
		overflow-y: auto;
		padding: 22px 28px 20px;
	}

	.form-section + .form-section {
		margin-top: 26px;
	}
	.section-title {
		font-size: 13px;
		font-weight: 600;
		color: var(--ant-text-secondary);
		letter-spacing: 0.03em;
		text-transform: uppercase;
		margin-bottom: 12px;
		padding-bottom: 8px;
		border-bottom: 1px dashed var(--ant-border-split);
	}

	.form-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px 14px;
	}
	.form-row {
		margin-bottom: 0;
	}
	.form-row-full {
		grid-column: 1 / -1;
	}
	.form-label {
		display: block;
		font-size: 13px;
		color: var(--ant-text-secondary);
		margin-bottom: 6px;
		font-weight: 500;
	}
	.muted {
		color: hsl(var(--bc)/0.4);
		font-weight: 400;
		font-size: 12px;
	}

	.admin-input {
		width: 100%;
		height: 34px;
		padding: 5px 12px;
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
	.admin-input:disabled,
	.admin-input[readonly] {
		background: hsl(var(--b2));
		cursor: not-allowed;
		opacity: 0.85;
	}
	.admin-textarea {
		min-height: 88px;
		resize: vertical;
		line-height: 1.6;
		height: auto;
		padding: 7px 12px;
	}

	.admin-select {
		width: 100%;
		height: 34px;
		padding: 5px 36px 5px 12px;
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
	.admin-select:disabled {
		background: hsl(var(--b2));
		cursor: not-allowed;
		opacity: 0.85;
	}

	.admin-toggle {
		appearance: none;
		width: 44px;
		height: 22px;
		border-radius: 9999px;
		background: var(--ant-border-color);
		cursor: pointer;
		position: relative;
		transition: background 0.2s;
		flex-shrink: 0;
		border: none;
	}
	.admin-toggle:checked {
		background: var(--ant-primary);
	}
	.admin-toggle::before {
		content: '';
		position: absolute;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #fff;
		top: 2px;
		left: 2px;
		transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}
	.admin-toggle:checked::before {
		transform: translateX(22px);
	}
	.admin-toggle:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	.switch-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.switch-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 14px;
		padding: 13px 16px;
		border-radius: var(--ant-radius);
		border: 1px solid var(--ant-border-color-secondary);
		background: var(--ant-bg-body);
		cursor: pointer;
		transition: all 0.15s;
	}
	.switch-item:hover {
		border-color: var(--ant-border-color);
	}
	.switch-item:has(.admin-toggle:disabled) {
		cursor: default;
	}
	.switch-text {
		min-width: 0;
		flex: 1;
	}
	.switch-title {
		font-size: 14px;
		font-weight: 500;
		color: var(--ant-text-primary);
		line-height: 1.4;
	}
	.switch-desc {
		font-size: 12px;
		color: hsl(var(--bc)/0.55);
		margin-top: 2px;
		line-height: 1.5;
	}

	.drawer-footer {
		padding: 14px 20px;
		border-top: 1px solid var(--ant-border-split);
		background: var(--ant-bg-body);
		display: flex;
		flex-direction: column;
		gap: 10px;
		flex-shrink: 0;
	}
	.drawer-footer-actions {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
		justify-content: space-between;
	}
	.drawer-footer > div:last-child {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
	}

	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 7px 14px;
		border-radius: var(--ant-radius-sm);
		border: 1px solid var(--ant-border-color);
		background: hsl(var(--b1));
		color: hsl(var(--bc));
		cursor: pointer;
		font-size: 14px;
		font-weight: 400;
		transition: all 0.15s;
		font-family: inherit;
		line-height: 1.5;
		white-space: nowrap;
		height: 34px;
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
	.btn-primary:hover:not(:disabled) { filter: brightness(0.92); }
	.btn-warning {
		background: #f59e0b;
		border-color: #f59e0b;
		color: #fff;
	}
	.btn-warning:hover:not(:disabled) { filter: brightness(0.92); }
	.btn-success {
		background: #10b981;
		border-color: #10b981;
		color: #fff;
	}
	.btn-success:hover:not(:disabled) { filter: brightness(0.92); }
	.btn-error {
		background: #ef4444;
		border-color: #ef4444;
		color: #fff;
	}
	.btn-error:hover:not(:disabled) { filter: brightness(0.92); }

	/* ========= Modal ========= */
	.modal-mask {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		backdrop-filter: blur(4px);
		-webkit-backdrop-filter: blur(4px);
		z-index: 1050;
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
		max-width: 500px;
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
		padding: 16px 22px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1px solid var(--ant-border-split);
		flex-shrink: 0;
	}
	.admin-modal-title {
		font-size: 15.5px;
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
		padding: 22px;
		overflow-y: auto;
		flex: 1;
	}
	.admin-modal-footer {
		padding: 12px 22px;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 8px;
		border-top: 1px solid var(--ant-border-split);
		flex-shrink: 0;
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

	@media (max-width: 560px) {
		.form-grid {
			grid-template-columns: 1fr;
		}
		.drawer-stats {
			grid-template-columns: repeat(2, 1fr);
		}
	}
</style>
