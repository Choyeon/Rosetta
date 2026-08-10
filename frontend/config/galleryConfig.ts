import { GalleryConfigSchema, type GalleryConfig } from "../types/galleryConfig";

const raw: Partial<GalleryConfig> = {};

const result = GalleryConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/galleryConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const galleryConfig: GalleryConfig = result.success ? result.data : GalleryConfigSchema.parse({});

export default galleryConfig;
