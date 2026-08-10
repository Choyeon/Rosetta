import { BangumiConfigSchema, type BangumiConfig } from "../types/bangumi";

const raw: Partial<BangumiConfig> = {};

const result = BangumiConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/bangumi] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const bangumi: BangumiConfig = result.success ? result.data : BangumiConfigSchema.parse({});

export default bangumi;
