import { DynamicConfigSchema, type DynamicConfig } from "../types/dynamicConfig";

const raw: Partial<DynamicConfig> = {};

const result = DynamicConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/dynamicConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const dynamicConfig: DynamicConfig = result.success ? result.data : DynamicConfigSchema.parse({});

export default dynamicConfig;
