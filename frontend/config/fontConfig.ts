import { FontConfigSchema, type FontConfig } from "../types/fontConfig";

const raw: Partial<FontConfig> = {};

const result = FontConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/fontConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const fontConfig: FontConfig = result.success ? result.data : FontConfigSchema.parse({});

export default fontConfig;
