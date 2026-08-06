import { apiDelete, apiGet, apiPost } from "./client";

/**
 * 评论前端类型（对齐后端 schemas.CommentResponse）
 *   author_avatar: 永远不暴露 email，只返回头像 URL（Gravatar md5 或用户上传头像）
 *   replies: 根评论里最多预取 3 条最新回复
 */
export interface RosettaComment {
	id: number;
	post_id: number;
	user_id: number | null;
	author_name: string;
	author_avatar: string;
	author_website: string | null;
	content: string;
	parent_id: number | null;
	status: "approved" | "pending" | "rejected" | "spam";
	is_pinned: boolean;
	likes_count: number;
	reply_total: number;
	created_at: string;
	replies: RosettaComment[];
	qq?: string | null;
	github?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
	resolved_avatar_url?: string | null;
}

export interface RosettaCommentPagedResponse {
	total: number;
	page: number;
	page_size: number;
	items: RosettaComment[];
}

export interface RosettaCommentCreate {
	parent_id?: number | null;
	author_name?: string | null;
	author_email?: string | null;
	author_website?: string | null;
	content: string;
	hcaptcha_token?: string | null;
	qq?: string;
	github?: string;
	author_avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
}

/* ---------------- 公共接口：任意用户 ---------------- */

/**
 * 获取某篇文章的根评论列表（含最多 3 条最新回复预览 + reply_total）
 *   include_unapproved=true：当前登录用户可以看到自己写的 pending 评论；
 *   管理员可以看到全部 pending。默认 false（仅已批准）。
 */
export function listPostComments(
	postIdOrSlug: number | string,
	params?: {
		page?: number;
		page_size?: number;
		include_unapproved?: boolean;
	},
) {
	return apiGet<RosettaCommentPagedResponse>(
		`/posts/${String(postIdOrSlug)}/comments`,
		params,
	);
}

/** 取某条根评论下全部回复（按 created_at 正序） */
export function listCommentReplies(
	commentId: number,
	params?: { page?: number; page_size?: number },
) {
	return apiGet<RosettaCommentPagedResponse>(
		`/comments/${commentId}/replies`,
		params,
	);
}

/** 发表评论（游客/登录皆可）。201 返回 CommentResponse */
export function createPostComment(
	postIdOrSlug: number | string,
	payload: RosettaCommentCreate,
) {
	return apiPost<RosettaComment>(
		`/posts/${String(postIdOrSlug)}/comments`,
		payload,
	);
}

/** 点赞（匿名/登录皆可；无去重，简单计数）返回 {likes_count} */
export function likeComment(commentId: number) {
	return apiPost<{ likes_count: number }>(`/comments/${commentId}/like`);
}

/* ---------------- 管理员接口 ---------------- */

export interface AdminCommentListParams {
	status?: "pending" | "approved" | "rejected" | "spam";
	page?: number;
	page_size?: number;
}

export function adminListComments(params?: AdminCommentListParams) {
	return apiGet<RosettaCommentPagedResponse>("/admin/comments", params);
}

export function adminApproveComment(id: number) {
	return apiPost<RosettaComment>(`/admin/comments/${id}/approve`);
}

export function adminRejectComment(id: number) {
	return apiPost<RosettaComment>(`/admin/comments/${id}/reject`);
}

export function adminMarkSpamComment(id: number) {
	return apiPost<RosettaComment>(`/admin/comments/${id}/spam`);
}

export function adminBatchComments(payload: {
	ids: number[];
	action: "approve" | "reject" | "spam" | "delete";
}) {
	return apiPost<{ success_count: number }>("/admin/comments/batch", payload);
}

export function adminDeleteComment(id: number) {
	return apiDelete<void>(`/admin/comments/${id}`);
}
