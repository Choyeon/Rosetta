import { OobeConfigSchema, type OobeConfig } from "../types/oobe";

const raw: Partial<OobeConfig> = {};

const result = OobeConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/oobe] schema 校验失败，使用默认值兜底:", result.error.issues);
}

const oobe: OobeConfig = result.success ? result.data : OobeConfigSchema.parse({});

export default oobe;
