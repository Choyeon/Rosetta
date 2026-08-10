import { AnnouncementConfigSchema, type AnnouncementConfig } from "../types/announcementConfig";

const raw: Partial<AnnouncementConfig> = {};

const result = AnnouncementConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/announcementConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const announcementConfig: AnnouncementConfig = result.success ? result.data : AnnouncementConfigSchema.parse({});

export default announcementConfig;
