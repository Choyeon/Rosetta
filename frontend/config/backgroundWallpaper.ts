import { BackgroundWallpaperConfigSchema, type BackgroundWallpaperConfig } from "../types/backgroundWallpaper";

const raw: Partial<BackgroundWallpaperConfig> = {};

const result = BackgroundWallpaperConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/backgroundWallpaper] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const backgroundWallpaper: BackgroundWallpaperConfig = result.success ? result.data : BackgroundWallpaperConfigSchema.parse({});

export default backgroundWallpaper;
