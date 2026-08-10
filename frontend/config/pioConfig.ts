import { PioConfigSchema, type PioConfig } from "../types/pioConfig";

const raw: Partial<PioConfig> = {};

const result = PioConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/pioConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const pioConfig: PioConfig = result.success ? result.data : PioConfigSchema.parse({});

export default pioConfig;
