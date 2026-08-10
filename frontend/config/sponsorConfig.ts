import { SponsorConfigSchema, type SponsorConfig } from "../types/sponsorConfig";

const raw: Partial<SponsorConfig> = {};

const result = SponsorConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/sponsorConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const sponsorConfig: SponsorConfig = result.success ? result.data : SponsorConfigSchema.parse({});

export default sponsorConfig;
