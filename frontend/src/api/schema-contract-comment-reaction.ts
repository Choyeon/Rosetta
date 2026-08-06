export type CommentReactionType =
	| "like"
	| "love"
	| "laugh"
	| "wow"
	| "sad"
	| "angry"
	| string;

export interface CommentReactionCreate {
	comment_id: number;
	reaction_type: CommentReactionType;
}

export interface CommentReactionResponse {
	id: number;
	comment_id: number;
	user_id: number | null;
	reaction_type: CommentReactionType;
	created_at: string;
}
