import { MusicConfigSchema, type MusicConfig } from "../types/musicConfig";

const raw: Partial<MusicConfig> = {};

const result = MusicConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/musicConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const musicConfig: MusicConfig = result.success ? result.data : MusicConfigSchema.parse({});

export default musicConfig;
