import { PlantumlConfigSchema, type PlantumlConfig } from "../types/plantumlConfig";

const raw: Partial<PlantumlConfig> = {};

const result = PlantumlConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/plantumlConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const plantumlConfig: PlantumlConfig = result.success ? result.data : PlantumlConfigSchema.parse({});

export default plantumlConfig;
