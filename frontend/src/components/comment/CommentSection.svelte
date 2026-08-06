<script lang="ts">
import { onMount } from "svelte";
import { getAuthToken } from "@/api/client";
import {
	createPostComment,
	listPostComments,
	type RosettaComment,
	type RosettaCommentPagedResponse,
} from "@/api/comments";
import { getCurrentUser } from "@/api/users";
import Icon from "@/components/common/Icon.svelte";
import {
	type AvatarSource,
	previewAvatarUrl as computePreviewAvatar,
	type GuestProfile,
	loadGuestProfile,
	saveGuestProfile,
} from "@/utils/avatarPreview";
import CommentItem from "./CommentItem.svelte";

interface Props {
	/** 文章 slug 或 id（按后端 URL: /api/posts/{post_id_or_slug}/comments 都接受） */
	postId: number | string;
	/** 文章标题，空状态里展示 */
	postTitle?: string;
}

const { postId, postTitle }: Props = $props();

let mounted = $state(false);
let loading = $state(true);
let error = $state<string | null>(null);
let data = $state<RosettaCommentPagedResponse | null>(null);
let totalCount = $state(0);
let page = $state(1);
let pageSize = $state(10);
let includeUnapproved = $state(false);

// 发表表单：登录态 vs 游客
let isLoggedIn = $state(false);
let guestName = $state("");
let guestEmail = $state("");
let guestWebsite = $state("");
let authorNameFromJwt = $state<string | null>(null);
// 游客 QQ / GitHub / 头像源
let guestQQ = $state("");
let guestGithub = $state("");
let authorAvatarSource = $state<AvatarSource>("auto");
// 登录态用户资料（若 getCurrentUser 成功）
let currentUser = $state<Awaited<ReturnType<typeof getCurrentUser>> | null>(
	null,
);

let content = $state("");
let contentSending = $state(false);
let pendingTipVisible = $state(false);

let previewAvatar = $derived<string | null>(
	isLoggedIn && currentUser
		? ((currentUser as any).resolved_avatar_url ??
				computePreviewAvatar({
					avatar: (currentUser as any).avatar,
					github: (currentUser as any).github,
					qq: (currentUser as any).qq,
					email: (currentUser as any).email,
					avatar_source: (currentUser as any).avatar_source ?? "auto",
				}) ??
				null)
		: computePreviewAvatar({
				avatar: null,
				github: guestGithub,
				qq: guestQQ,
				email: guestEmail,
				avatar_source: authorAvatarSource,
			}),
);

onMount(() => {
	mounted = true;
	const token = getAuthToken();
	isLoggedIn = !!token;
	if (token) {
		try {
			const payload = token.split(".")[1];
			if (payload) {
				const decoded = JSON.parse(atob(payload));
				authorNameFromJwt =
					decoded.nickname || decoded.username || decoded.sub || null;
			}
		} catch {
			/* ignore */
		}
	}
	// 本地记忆回填
	const saved = loadGuestProfile();
	if (saved && !isLoggedIn) {
		guestName = saved.name ?? "";
		guestEmail = saved.email ?? "";
		guestWebsite = saved.website ?? "";
		guestQQ = saved.qq ?? "";
		guestGithub = saved.github ?? "";
	}
	// 登录态：拉当前用户资料（失败静默 fallback JWT）
	if (isLoggedIn) {
		(getCurrentUser() as any).then(
			(u: any) => {
				currentUser = u;
				if (u)
					authorNameFromJwt = u.nickname || u.username || authorNameFromJwt;
			},
			() => {
				/* ignore */
			},
		);
	}
	load();
});

function resetAndRevealTip(status: string) {
	pendingTipVisible = status === "pending" || status === "rejected";
	if (pendingTipVisible) {
		window.setTimeout(() => {
			pendingTipVisible = false;
		}, 4000);
	}
}

async function load(reloadPage = false) {
	if (reloadPage) page = 1;
	loading = true;
	error = null;
	try {
		const r = await listPostComments(postId, {
			page,
			page_size: pageSize,
			include_unapproved: includeUnapproved,
		});
		data = r;
		totalCount = r.total ?? r.items?.length ?? 0;
	} catch (e: unknown) {
		const msg = e instanceof Error ? e.message : "加载评论失败，请稍后重试";
		error = msg;
		// eslint-disable-next-line no-alert
		alert(msg);
	} finally {
		loading = false;
	}
}

function avatarFallbackInitial(name: string): string {
	const s = (name || "?").trim();
	return s ? s.slice(0, 1).toUpperCase() : "?";
}

function onSelfUpdated(_item: RosettaComment) {
	/* 未来：可以在这里做点赞同步到全局统计；目前直接更新局部即可 */
}

async function onSubmit() {
	const trimmed = content.trim();
	if (trimmed.length < 2 || trimmed.length > 3000 || contentSending) return;

	// 游客：校验 author_name 长度
	let author_name = "";
	if (!isLoggedIn) {
		author_name = (guestName || "").trim();
		if (author_name.length < 2 || author_name.length > 30) {
			// eslint-disable-next-line no-alert
			alert("昵称长度需要 2-30 个字符");
			return;
		}
		if (guestEmail) {
			const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
			if (!emailRe.test(guestEmail.trim())) {
				// eslint-disable-next-line no-alert
				alert("邮箱格式不正确");
				return;
			}
		}
		if (guestWebsite) {
			const trimmedUrl = guestWebsite.trim();
			if (!/^https?:\/\//i.test(trimmedUrl)) {
				// eslint-disable-next-line no-alert
				alert("网站需要以 http:// 或 https:// 开头");
				return;
			}
		}
		// QQ 校验（非空）
		if (guestQQ) {
			const ok = /^\d{5,11}$/.test(guestQQ.trim());
			if (!ok) {
				alert("QQ 号需要 5-11 位纯数字");
				return;
			}
		}
		// GitHub 校验（非空）
		if (guestGithub) {
			const ok =
				/^(https?:\/\/github\.com\/|@)?[a-zA-Z0-9](?:-?[a-zA-Z0-9]){0,38}\/?$/.test(
					guestGithub.trim(),
				);
			if (!ok) {
				alert("GitHub 格式不正确（支持 @用户名或完整链接）");
				return;
			}
		}
	}

	contentSending = true;
	try {
		const created = await createPostComment(postId, {
			author_name: isLoggedIn ? authorNameFromJwt || undefined : author_name,
			author_email: isLoggedIn ? undefined : guestEmail.trim() || undefined,
			author_website: isLoggedIn ? undefined : guestWebsite.trim() || undefined,
			content: trimmed,
			qq: isLoggedIn ? undefined : guestQQ.trim() || undefined,
			github: isLoggedIn ? undefined : guestGithub.trim() || undefined,
			author_avatar_source:
				isLoggedIn || authorAvatarSource === "auto"
					? undefined
					: authorAvatarSource,
		});

		// 前端乐观插入到列表合适位置
		if (!data) {
			data = { total: 0, page: 1, page_size: pageSize, items: [] };
		}
		if (created.parent_id == null || created.parent_id === undefined) {
			// 根评论：插到 items 最前面（时间倒序 on top，和后端一致）
			const items = [created, ...data.items];
			// 超过 pageSize 则截断，保留最新 pageSize 条（前端展示简单）
			data.items = items.slice(0, pageSize);
			data.total = data.total + 1;
			totalCount = data.total;
		}
		content = "";
		resetAndRevealTip(created.status);
		if (!isLoggedIn) {
			saveGuestProfile({
				name: guestName,
				email: guestEmail,
				website: guestWebsite,
				qq: guestQQ,
				github: guestGithub,
				savedAt: Date.now(),
			});
		}
	} catch (e: unknown) {
		const msg = e instanceof Error ? e.message : "发送评论失败，请稍后重试";
		// eslint-disable-next-line no-alert
		alert(msg);
	} finally {
		contentSending = false;
	}
}

function onPrevPage() {
	if (page > 1) {
		page = page - 1;
		load();
	}
}
function onNextPage() {
	if (data && page * pageSize < data.total) {
		page = page + 1;
		load();
	}
}
</script>

<div
	id="post-comments"
	class="card-base p-4 sm:p-6 md:p-8 mb-6 relative overflow-hidden"
>
	<!-- 装饰性背景 -->
	<div class="absolute top-0 right-0 w-32 h-32 opacity-5 pointer-events-none">
		<svg viewBox="0 0 100 100" class="w-full h-full">
			<circle cx="50" cy="50" r="40" fill="currentColor" class="text-(--primary)" />
			<circle
				cx="50"
				cy="50"
				r="25"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				class="text-(--primary)"
			/>
			<circle cx="50" cy="50" r="10" fill="currentColor" class="text-(--primary)" />
		</svg>
	</div>

	<!-- 顶部统计 + 刷新 -->
	<div class="relative z-10 mb-5 sm:mb-6">
		<div class="flex items-center gap-3 mb-2">
			<div class="w-1 h-6 bg-linear-to-b from-(--primary) to-transparent rounded-full"></div>
			<h3 class="text-xl font-bold text-(--btn-content)">
				{mounted && totalCount > 0 ? `共 ${totalCount} 条评论` : "评论"}
			</h3>
			<button
				type="button"
				onclick={() => load(true)}
				title="刷新评论"
				disabled={loading}
				class:list={[
					"ml-auto inline-flex items-center gap-1 text-sm px-2 py-1 rounded-md transition",
					"hover:bg-(--enter-btn-bg) text-(--content-meta) hover:text-(--primary) active:scale-95",
					loading ? "opacity-60 cursor-wait" : "",
				]}
			>
				<Icon
					icon="material-symbols:refresh-rounded"
					class={loading ? "animate-spin" : ""}
					width="16"
					height="16"
				/>
				刷新
			</button>
		</div>
		<p class="text-sm text-(--content-meta) ml-4">
			欢迎理性讨论，畅所欲言。支持嵌套回复（最多 1 层）。
		</p>
	</div>

	<!-- 发表评论表单 -->
	<div class="relative z-10 mb-6 pl-0 sm:pl-2">
		<div class="flex gap-3">
			<!-- 预览头像（登录/游客统一显示；图片 load 失败 fallback 首字母） -->
			<div class="hidden sm:flex shrink-0 w-10 h-10 rounded-full items-center justify-center text-sm font-bold text-white ring-1 ring-black/5 dark:ring-white/10 select-none overflow-hidden"
				 style="background-color: hsl(210, 70%, 60%);">
				{#if previewAvatar}
					<img src={previewAvatar} alt="" class="w-full h-full object-cover"
						 onerror={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
				{:else}
					<span>{avatarFallbackInitial(
						isLoggedIn ? (authorNameFromJwt || (currentUser as any)?.nickname || 'U') : (guestName || 'G')
					)}</span>
				{/if}
			</div>
			<div class="flex-1 min-w-0 flex flex-col gap-2">
				{#if !isLoggedIn}
					<!-- 游客字段：窄屏纵向排列 -->
					<div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
						<input
							bind:value={guestName}
							type="text"
							maxlength={30}
							placeholder="昵称（必填，2-30）"
							class="w-full px-3 py-2 text-sm rounded-lg bg-white dark:bg-black/20 ring-1 ring-(--line-divider) focus:ring-2 focus:ring-(--primary)/60 outline-none transition text-(--btn-content)"
						/>
						<input
							bind:value={guestEmail}
							type="email"
							maxlength={254}
							placeholder="邮箱（可选，用于接收回复通知和 Gravatar 头像）"
							class="w-full px-3 py-2 text-sm rounded-lg bg-white dark:bg-black/20 ring-1 ring-(--line-divider) focus:ring-2 focus:ring-(--primary)/60 outline-none transition text-(--btn-content)"
						/>
						<input
							bind:value={guestWebsite}
							type="url"
							maxlength={200}
							placeholder="个人网站（可选，http(s):// 开头）"
							class="w-full px-3 py-2 text-sm rounded-lg bg-white dark:bg-black/20 ring-1 ring-(--line-divider) focus:ring-2 focus:ring-(--primary)/60 outline-none transition text-(--btn-content)"
						/>
					</div>
					<!-- 新增：QQ + GitHub 第二行（sm:grid-cols-2） -->
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
						<input bind:value={guestQQ}
							   type="text" inputmode="numeric" pattern="\d{5,11}" maxlength={11}
							   placeholder="QQ（选填，自动拉头像）"
							   class="w-full px-3 py-2 text-sm rounded-lg bg-white dark:bg-black/20 ring-1 ring-(--line-divider) focus:ring-2 focus:ring-(--primary)/60 outline-none transition text-(--btn-content)" />
						<input bind:value={guestGithub}
							   type="text" maxlength={64}
							   placeholder="GitHub（选填，@用户名或链接，头像优先级最高）"
							   class="w-full px-3 py-2 text-sm rounded-lg bg-white dark:bg-black/20 ring-1 ring-(--line-divider) focus:ring-2 focus:ring-(--primary)/60 outline-none transition text-(--btn-content)" />
					</div>
				{:else}
					<div class="text-sm text-(--content-meta)">
						已登录身份：<span class="font-medium text-(--btn-content)">
							{authorNameFromJwt || "用户"}
						</span>
						{#if (currentUser as any)?.qq || (currentUser as any)?.github}
							<span class="ml-2 text-[11px] text-(--primary) rounded-full bg-(--primary)/8 px-2 py-0.5">
								头像：{(currentUser as any).avatar_source ?? 'auto'}
							</span>
						{/if}
					</div>
				{/if}

				<textarea
					bind:value={content}
					rows={4}
					maxlength={3000}
					placeholder={isLoggedIn
						? "写下你的评论（2-3000 字）…"
						: "先留下昵称，再来写点什么（2-3000 字）…"}
					class="w-full resize-y rounded-xl bg-white dark:bg-black/20 px-3 sm:px-4 py-2 sm:py-3 text-sm ring-1 ring-(--line-divider) focus:ring-2 focus:ring-(--primary)/60 outline-none transition text-(--btn-content)"
				/>

				<div class="flex flex-wrap items-center justify-between gap-2">
					<div class="text-[11px] tabular-nums text-(--content-meta)">
						{content.length} / 3000
						{#if pendingTipVisible}
							<span class="ml-3 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-300">
								<Icon icon="material-symbols:info-rounded" width="12" height="12" />
								评论已提交，等待审核，通过后会公开显示。
							</span>
						{/if}
					</div>
					<button
						type="button"
						onclick={onSubmit}
						disabled={contentSending ||
							content.trim().length < 2 ||
							content.length > 3000 ||
							(!isLoggedIn && (guestName.trim().length < 2 || guestName.trim().length > 30))}
						class:list={[
							"inline-flex items-center gap-2 px-4 sm:px-5 py-2 rounded-lg text-sm font-medium",
							"bg-(--primary) text-white dark:text-black/80 hover:bg-(--primary)/90",
							"active:scale-95 transition disabled:opacity-50 disabled:cursor-not-allowed",
						]}
					>
						{#if contentSending}
							<Icon icon="svg-spinners:ring-resize" width="14" height="14" />
							发送中
						{:else}
							<Icon icon="material-symbols:send-rounded" width="16" height="16" />
							发送
						{/if}
					</button>
				</div>
			</div>
		</div>
	</div>

	<!-- 骨架屏 / 空状态 / 错误 / 列表 -->
	<div class="relative z-10 pl-0 sm:pl-2 pr-0 sm:pr-2">
		{#if loading && !data}
			<!-- 骨架屏 6 条 -->
			<div class="flex flex-col gap-4">
				{#each Array(6) as _, i (i)}
					<div class="flex gap-3 animate-pulse">
						<div class="w-10 h-10 rounded-full bg-(--btn-regular-bg)" />
						<div class="flex-1 min-w-0 space-y-2">
							<div class="h-3 w-1/3 rounded bg-(--btn-regular-bg)" />
							<div class="h-2.5 w-full rounded bg-(--btn-regular-bg)" />
							<div class="h-2.5 w-5/6 rounded bg-(--btn-regular-bg)" />
							<div class="h-2.5 w-2/3 rounded bg-(--btn-regular-bg)" />
						</div>
					</div>
				{/each}
			</div>
		{:else if error}
			<div class="text-center py-10 text-(--content-meta)">
				<p class="mb-4">加载评论失败：{error}</p>
				<button
					type="button"
					onclick={() => load(true)}
					class="px-4 py-2 rounded-lg bg-(--primary)/10 text-(--primary) text-sm hover:bg-(--primary)/20 active:scale-95 transition"
				>
					重试加载
				</button>
			</div>
		{:else if !data || data.items.length === 0}
			<!-- 插画式空状态：抢沙发 -->
			<div class="flex flex-col items-center justify-center py-12 text-center">
				<div
					class="relative w-24 h-24 mb-4 rounded-full bg-(--primary)/10 flex items-center justify-center"
				>
					<div class="absolute inset-0 rounded-full border-4 border-dashed border-(--primary)/20 animate-[spin_16s_linear_infinite]" />
					<Icon
						icon="material-symbols:chat-bubble-outline-rounded"
						width="44"
						height="44"
						class="text-(--primary)"
					/>
				</div>
				<p class="text-lg font-semibold text-(--btn-content) mb-1">还没有评论</p>
				<p class="text-sm text-(--content-meta) mb-4">
					抢沙发，来为《{postTitle || "这篇文章"}》写第一条评论吧！
				</p>
				<button
					type="button"
					onclick={() => load(true)}
					class="text-xs text-(--content-meta) hover:text-(--primary) underline-offset-2 hover:underline"
				>
					如果刚刚有人评论，点这里刷新
				</button>
			</div>
		{:else}
			<!-- 评论列表（根评论按时间倒序：最新 on top；每个评论的回复按时间正序由后端保证） -->
			<div class="flex flex-col gap-5 sm:gap-6">
				{#each data.items as c (c.id)}
					<CommentItem
						comment={c}
						depth={0}
						postId={postId}
						onSelfUpdated={onSelfUpdated}
					/>
				{/each}
			</div>

			<!-- 分页 -->
			{#if data.total > pageSize}
				<div class="mt-6 flex items-center justify-between text-sm">
					<button
						type="button"
						onclick={onPrevPage}
						disabled={page <= 1}
						class="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-(--content-meta) hover:bg-(--enter-btn-bg) disabled:opacity-40 disabled:cursor-not-allowed transition"
					>
						<Icon icon="material-symbols:chevron-left-rounded" width="16" height="16" />
						上一页
					</button>
					<span class="tabular-nums text-(--content-meta)">
						第 {page} 页 / 共 {Math.max(1, Math.ceil(data.total / pageSize))} 页
					</span>
					<button
						type="button"
						onclick={onNextPage}
						disabled={page * pageSize >= data.total}
						class="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-(--content-meta) hover:bg-(--enter-btn-bg) disabled:opacity-40 disabled:cursor-not-allowed transition"
					>
						下一页
						<Icon icon="material-symbols:chevron-right-rounded" width="16" height="16" />
					</button>
				</div>
			{/if}
		{/if}
	</div>
</div>
