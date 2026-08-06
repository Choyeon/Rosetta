<script lang="ts">
import { onMount } from "svelte";
import {
	createPostComment,
	likeComment,
	listCommentReplies,
	type RosettaComment,
} from "@/api/comments";
import Icon from "@/components/common/Icon.svelte";
import CommentItem from "./CommentItem.svelte";

interface Props {
	comment: RosettaComment;
	depth?: number;
	postId: number | string;
	onNewReply?: (reply: RosettaComment) => void;
	onSelfUpdated?: (updated: RosettaComment) => void;
}

const {
	comment,
	depth = 0,
	postId,
	onNewReply,
	onSelfUpdated,
}: Props = $props();

let mounted = $state(false);
let showReplyForm = $state(false);
let loadingReplies = $state(false);
let repliesLoadedAll = $state(false);
let likeThrottleUntil = $state(0);
let likeLoading = $state(false);
let replyContent = $state("");
let replySending = $state(false);
let localLikes = $state(comment.likes_count);

onMount(() => {
	mounted = true;
	repliesLoadedAll =
		comment.reply_total <= 0 || comment.replies.length >= comment.reply_total;
});

// 相对时间（Intl.RelativeTimeFormat）
const rtf = new Intl.RelativeTimeFormat("zh-CN", { numeric: "auto" });
function relative(iso: string): string {
	const diffMs = new Date(iso).getTime() - Date.now();
	const abs = Math.abs(diffMs);
	const sec = Math.round(diffMs / 1000);
	if (abs < 60_000) return rtf.format(sec, "second");
	const min = Math.round(sec / 60);
	if (abs < 3_600_000) return rtf.format(min, "minute");
	const hour = Math.round(min / 60);
	if (abs < 86_400_000) return rtf.format(hour, "hour");
	const day = Math.round(hour / 24);
	if (abs < 86_400_000 * 30) return rtf.format(day, "day");
	return new Date(iso).toLocaleDateString("zh-CN");
}

// 把 plain text 的 URL 自动变成 <a target=_blank>
const URL_RE = /(https?:\/\/[^\s<>"`'）】]+)/g;
function linkifiedHtml(text: string): string {
	const escaped = text
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
	return escaped.replace(
		URL_RE,
		(u) =>
			`<a href="${u}" target="_blank" rel="noopener noreferrer nofollow" class="text-(--primary) underline-offset-2 hover:underline">${u}</a>`,
	);
}

function avatarFallbackInitial(name: string): string {
	const s = (name || "?").trim();
	return s ? s.slice(0, 1).toUpperCase() : "?";
}

function statusBadgeClass(status: RosettaComment["status"]): string {
	switch (status) {
		case "pending":
			return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300";
		case "rejected":
			return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
		case "spam":
			return "bg-gray-200 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
		default:
			return "hidden";
	}
}

function statusBadgeText(status: RosettaComment["status"]): string {
	switch (status) {
		case "pending":
			return "待审核";
		case "rejected":
			return "已拒绝";
		case "spam":
			return "垃圾";
		default:
			return "";
	}
}

async function onLikeClick() {
	if (!mounted) return;
	const now = Date.now();
	if (likeLoading) return;
	if (now < likeThrottleUntil) return;
	likeThrottleUntil = now + 3000; // 3 秒节流
	likeLoading = true;
	try {
		const r = await likeComment(comment.id);
		localLikes = Number(r.likes_count ?? localLikes + 1);
		comment.likes_count = localLikes;
		onSelfUpdated?.(comment);
	} catch (e: unknown) {
		const msg = e instanceof Error ? e.message : "点赞失败，请稍后重试";
		// eslint-disable-next-line no-alert
		alert(msg);
	} finally {
		likeLoading = false;
	}
}

async function onLoadAllReplies() {
	if (loadingReplies || repliesLoadedAll) return;
	loadingReplies = true;
	try {
		const page = 1;
		const page_size = Math.max(
			comment.reply_total,
			comment.replies.length + 50,
		);
		const r = await listCommentReplies(comment.id, { page, page_size });
		comment.replies = r.items ?? [];
		repliesLoadedAll = true;
	} catch (e: unknown) {
		const msg = e instanceof Error ? e.message : "加载回复失败";
		// eslint-disable-next-line no-alert
		alert(msg);
	} finally {
		loadingReplies = false;
	}
}

function openReply() {
	showReplyForm = true;
}
function cancelReply() {
	showReplyForm = false;
	replyContent = "";
}

async function submitReply() {
	const content = replyContent.trim();
	if (content.length < 2 || content.length > 3000 || replySending) return;
	replySending = true;
	try {
		const reply = await createPostComment(postId, {
			parent_id: comment.id,
			content,
		});
		// 成功后 push 到当前 replies
		if (!comment.replies) comment.replies = [];
		comment.replies = [...comment.replies, reply];
		comment.reply_total = comment.reply_total + 1;
		onNewReply?.(reply);
		replyContent = "";
		showReplyForm = false;
	} catch (e: unknown) {
		const msg = e instanceof Error ? e.message : "发送回复失败";
		// eslint-disable-next-line no-alert
		alert(msg);
	} finally {
		replySending = false;
	}
}

function onChildUpdated(child: RosettaComment) {
	const idx = comment.replies.findIndex((r) => r.id === child.id);
	if (idx >= 0) {
		const next = [...comment.replies];
		next[idx] = child;
		comment.replies = next;
	}
}
</script>

<div
	class:list={[
		"comment-item group flex gap-3 sm:gap-4 w-full relative",
		depth > 0 ? "pl-2 sm:pl-4 border-l border-(--line-divider)" : "pt-1",
	]}
>
	<!-- 头像 -->
	<div class="shrink-0">
		<div
			class:list={[
				"relative overflow-hidden rounded-full ring-1 ring-black/5 dark:ring-white/10 flex items-center justify-center select-none",
				depth === 0 ? "w-10 h-10 text-sm" : "w-8 h-8 text-xs",
			]}
			style="background-color: hsl({(comment.id * 137) % 360}, 60%, 60%); color: white;"
		>
			{#if ((comment as any).resolved_avatar_url ?? comment.author_avatar)}
				<img
					src={(comment as any).resolved_avatar_url ?? comment.author_avatar}
					alt={comment.author_name}
					loading="lazy"
					class="w-full h-full object-cover"
					onerror={(e) => {
						const el = e.currentTarget as HTMLImageElement;
						el.style.display = "none";
					}}
				/>
			{:else}
				<span class="font-bold">{avatarFallbackInitial(comment.author_name)}</span>
			{/if}
		</div>
	</div>

	<!-- 主体 -->
	<div class="flex-1 min-w-0">
		<div class="flex flex-wrap items-center gap-2 text-sm">
			{#if comment.author_website}
				<a
					href={comment.author_website}
					target="_blank"
					rel="noopener noreferrer nofollow"
					class="font-semibold text-(--primary) hover:underline truncate max-w-[50%]"
				>
					{comment.author_name}
				</a>
			{:else}
				<span
					class="font-semibold text-(--btn-content) truncate max-w-[50%]"
				>
					{comment.author_name}
				</span>
			{/if}

			{#if comment.is_pinned && depth === 0}
				<span
					class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded bg-(--primary)/10 text-(--primary)"
				>
					<Icon icon="material-symbols:pin-rounded" width="12" height="12" />
					置顶
				</span>
			{/if}

			<span class="px-1.5 py-0.5 rounded text-[10px] {statusBadgeClass(comment.status)}">
				{statusBadgeText(comment.status)}
			</span>

			<span class="text-xs text-(--content-meta)">
				{relative(comment.created_at)}
			</span>
		</div>

		<!-- 正文：pending 时灰显表示"待审核占位" -->
		<div
			class:list={[
				"mt-1 text-sm leading-relaxed whitespace-pre-wrap break-words markdown-content",
				comment.status === "pending" ? "text-(--content-meta) italic" : "",
				comment.status === "rejected" || comment.status === "spam"
					? "text-(--content-meta)/70 line-through decoration-(--content-meta)/40"
					: "text-(--btn-content)",
			]}
		>
			{@html linkifiedHtml(comment.content)}
		</div>

		<!-- 操作区 -->
		<div class="mt-2 flex items-center flex-wrap gap-3 text-xs">
			<button
				type="button"
				onclick={onLikeClick}
				disabled={likeLoading || Date.now() < likeThrottleUntil}
				class:list={[
					"inline-flex items-center gap-1 transition px-2 py-1 rounded-md",
					"hover:bg-(--enter-btn-bg) active:scale-95",
					likeLoading ? "opacity-60 cursor-wait" : "",
				]}
			>
				<Icon
					icon={localLikes > 0 ? "material-symbols:favorite-rounded" : "material-symbols:favorite-outline-rounded"}
					width="16"
					height="16"
					class={localLikes > 0 ? "text-red-500" : "text-(--content-meta)"}
				/>
				<span class="tabular-nums">{localLikes}</span>
			</button>

			{#if depth === 0}
				<button
					type="button"
					onclick={openReply}
					class="inline-flex items-center gap-1 px-2 py-1 rounded-md transition hover:bg-(--enter-btn-bg) active:scale-95 text-(--content-meta) hover:text-(--primary)"
				>
					<Icon icon="material-symbols:reply-rounded" width="16" height="16" />
					回复
				</button>
			{/if}
		</div>

		<!-- 回复输入框：depth=0 时才显示 -->
		{#if depth === 0 && showReplyForm}
			<div class="mt-3 p-3 rounded-xl bg-(--btn-regular-bg) ring-1 ring-black/5 dark:ring-white/10">
				<div class="text-xs text-(--content-meta) mb-2">
					回复给 <span class="text-(--btn-content) font-medium">@{comment.author_name}</span>
				</div>
				<textarea
					bind:value={replyContent}
					rows={3}
					maxlength={3000}
					placeholder="写下你的回复（2-3000 字）…"
					class="w-full resize-y rounded-lg bg-white dark:bg-black/20 px-3 py-2 text-sm ring-1 ring-(--line-divider) focus:ring-2 focus:ring-(--primary)/60 outline-none transition text-(--btn-content)"
				/>
				<div class="mt-2 flex items-center justify-between gap-2">
					<span class="text-[11px] tabular-nums text-(--content-meta)">
						{replyContent.length} / 3000
					</span>
					<div class="flex items-center gap-2">
						<button
							type="button"
							onclick={cancelReply}
							class="px-3 py-1.5 rounded-md text-sm text-(--content-meta) hover:bg-(--enter-btn-bg) active:scale-95 transition"
						>
							取消
						</button>
						<button
							type="button"
							onclick={submitReply}
							disabled={replySending || replyContent.trim().length < 2 || replyContent.length > 3000}
							class:list={[
								"inline-flex items-center gap-1 px-4 py-1.5 rounded-md text-sm font-medium text-white dark:text-black/80",
								"bg-(--primary) hover:bg-(--primary)/90 active:scale-95 transition disabled:opacity-50 disabled:cursor-not-allowed",
							]}
						>
							{#if replySending}
								<Icon icon="svg-spinners:ring-resize" width="14" height="14" />
								发送中
							{:else}
								发送
							{/if}
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- 回复列表（嵌套最多一层，depth=1 不再显示回复按钮/再嵌套） -->
		{#if comment.replies && comment.replies.length > 0}
			<div class="mt-3 flex flex-col gap-4">
				{#each comment.replies as r (r.id)}
					<CommentItem
						comment={r}
						depth={depth + 1}
						postId={postId}
						onNewReply={(reply) => onNewReply?.(reply)}
						onSelfUpdated={onChildUpdated}
					/>
				{/each}
			</div>
		{/if}

		<!-- 查看全部回复 -->
		{#if depth === 0 && comment.reply_total > comment.replies.length}
			<div class="mt-3">
				<button
					type="button"
					onclick={onLoadAllReplies}
					disabled={loadingReplies}
					class="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-sm text-(--primary) hover:bg-(--primary)/10 active:scale-95 transition"
				>
					{#if loadingReplies}
						<Icon icon="svg-spinners:ring-resize" width="14" height="14" />
						加载中…
					{:else}
						<Icon icon="material-symbols:expand-more-rounded" width="16" height="16" />
						查看全部 {comment.reply_total} 条回复
					{/if}
				</button>
			</div>
		{/if}
	</div>
</div>
