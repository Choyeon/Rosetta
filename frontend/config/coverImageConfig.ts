import { CoverImageConfigSchema, type CoverImageConfig } from "../types/coverImageConfig";

const raw: Partial<CoverImageConfig> = {};

const result = CoverImageConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/coverImageConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const coverImageConfig: CoverImageConfig = result.success ? result.data : CoverImageConfigSchema.parse({});

export default coverImageConfig;
