import { MermaidConfigSchema, type MermaidConfig } from "../types/mermaidConfig";

const raw: Partial<MermaidConfig> = {};

const result = MermaidConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/mermaidConfig] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const mermaidConfig: MermaidConfig = result.success ? result.data : MermaidConfigSchema.parse({});

export default mermaidConfig;
