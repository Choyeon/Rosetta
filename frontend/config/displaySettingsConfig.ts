import { DisplaySettingsConfigSchema, type DisplaySettingsConfig } from "../types/displaySettingsConfig";

const raw: Partial<DisplaySettingsConfig> = {};

const result = DisplaySettingsConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/displaySettingsConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const displaySettingsConfig: DisplaySettingsConfig = result.success ? result.data : DisplaySettingsConfigSchema.parse({});

export default displaySettingsConfig;
