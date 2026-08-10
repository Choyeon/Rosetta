import { FriendsConfigSchema, type FriendsConfig } from "../types/friendsConfig";

const raw: Partial<FriendsConfig> = {};

const result = FriendsConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/friendsConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const friendsConfig: FriendsConfig = result.success ? result.data : FriendsConfigSchema.parse({});

export default friendsConfig;
