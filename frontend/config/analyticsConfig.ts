import { AnalyticsConfigSchema, type AnalyticsConfig } from "../types/analyticsConfig";

const raw: Partial<AnalyticsConfig> = {};

const result = AnalyticsConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/analyticsConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const analyticsConfig: AnalyticsConfig = result.success ? result.data : AnalyticsConfigSchema.parse({});

export default analyticsConfig;
