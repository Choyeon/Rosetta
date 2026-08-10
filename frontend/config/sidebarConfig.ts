import { SidebarConfigSchema, type SidebarConfig } from "../types/sidebarConfig";

const raw: Partial<SidebarConfig> = {};

const result = SidebarConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/sidebarConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const sidebarConfig: SidebarConfig = result.success ? result.data : SidebarConfigSchema.parse({});

export default sidebarConfig;
