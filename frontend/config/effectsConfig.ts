import { EffectsConfigSchema, type EffectsConfig } from "../types/effectsConfig";

const raw: Partial<EffectsConfig> = {};

const result = EffectsConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/effectsConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const effectsConfig: EffectsConfig = result.success ? result.data : EffectsConfigSchema.parse({});

export default effectsConfig;
