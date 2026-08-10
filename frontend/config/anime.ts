import { AnimeConfigSchema, type AnimeConfig } from "../types/anime";

const raw: Partial<AnimeConfig> = {};

const result = AnimeConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/anime] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const anime: AnimeConfig = result.success ? result.data : AnimeConfigSchema.parse({});

export default anime;
