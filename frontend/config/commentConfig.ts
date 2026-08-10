import { CommentConfigSchema, type CommentConfig } from "../types/commentConfig";

const raw: Partial<CommentConfig> = {};

const result = CommentConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/commentConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const commentConfig: CommentConfig = result.success ? result.data : CommentConfigSchema.parse({});

export default commentConfig;
