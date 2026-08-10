import { ProfileConfigSchema, type ProfileConfig } from "../types/profileConfig";

const raw: Partial<ProfileConfig> = {};

const result = ProfileConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/profileConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const profileConfig: ProfileConfig = result.success ? result.data : ProfileConfigSchema.parse({});

export default profileConfig;
