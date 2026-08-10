import { LicenseConfigSchema, type LicenseConfig } from "../types/licenseConfig";

const raw: Partial<LicenseConfig> = {};

const result = LicenseConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/licenseConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const licenseConfig: LicenseConfig = result.success ? result.data : LicenseConfigSchema.parse({});

export default licenseConfig;
