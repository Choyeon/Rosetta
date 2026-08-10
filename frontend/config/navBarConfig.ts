import { NavBarConfigSchema, type NavBarConfig } from "../types/navBarConfig";

const raw: Partial<NavBarConfig> = {};

const result = NavBarConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/navBarConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const navBarConfig: NavBarConfig = result.success ? result.data : NavBarConfigSchema.parse({});

export default navBarConfig;
