import { FooterConfigSchema, type FooterConfig } from "../types/footerConfig";

const raw: Partial<FooterConfig> = {};

const result = FooterConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/footerConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const footerConfig: FooterConfig = result.success ? result.data : FooterConfigSchema.parse({});

export default footerConfig;
