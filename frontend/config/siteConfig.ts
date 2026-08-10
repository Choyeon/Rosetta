import { SiteConfigSchema, type SiteConfig } from "../types/siteConfig";

const raw: Partial<SiteConfig> = {};

const result = SiteConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/siteConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const siteConfig: SiteConfig = result.success ? result.data : SiteConfigSchema.parse({});

export default siteConfig;
