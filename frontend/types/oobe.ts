import { z } from "zod";

export const OobeStepSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().optional(),
  order: z.number().int().default(0),
  completed: z.boolean().default(false),
  required: z.boolean().default(true),
  skippable: z.boolean().default(false),
});

export type OobeStep = z.infer<typeof OobeStepSchema>;

export const OobeSitePayloadSchema = z.object({
  name: z.string().min(1),
  url: z.string().url(),
  description: z.string().default(""),
  subtitle: z.string().default(""),
  keywords: z.array(z.string()).default([]),
  locale: z.enum(["zh-CN", "zh-TW", "en", "ja"]).default("zh-CN"),
  timezone: z.string().default("Asia/Shanghai"),
});

export const OobeAdminPayloadSchema = z.object({
  username: z.string().min(3).max(64),
  password: z.string().min(8).max(128),
  email: z.string().email(),
  nickname: z.string().optional(),
});

export const OobeDatabasePayloadSchema = z.object({
  type: z.enum(["sqlite", "mysql", "postgresql"]).default("sqlite"),
  host: z.string().default("127.0.0.1"),
  port: z.number().int().positive().default(3306),
  database: z.string().default("rosetta"),
  username: z.string().default(""),
  password: z.string().default(""),
  sqlitePath: z.string().default("data/rosetta.db"),
  ssl: z.boolean().default(false),
  poolMin: z.number().int().nonnegative().default(1),
  poolMax: z.number().int().positive().default(10),
});

export const OobeStoragePayloadSchema = z.object({
  type: z.enum(["local", "s3", "oss", "cos", "qiniu", "r2"]).default("local"),
  localDir: z.string().default("media"),
  publicUrl: z.string().default("/media"),
  accessKeyId: z.string().default(""),
  accessKeySecret: z.string().default(""),
  region: z.string().default(""),
  bucket: z.string().default(""),
  endpoint: z.string().optional(),
  cdnUrl: z.string().optional(),
});

export const OobeConfigSchema = z.object({
  enabled: z.boolean().default(true),
  completed: z.boolean().default(false),
  token: z.string().optional(),
  expiresAt: z.string().datetime().optional(),
  steps: z.array(OobeStepSchema).default([
    { id: "welcome", title: "欢迎", order: 0, completed: false, skippable: true },
    { id: "site", title: "站点信息", order: 1, completed: false },
    { id: "admin", title: "管理员账号", order: 2, completed: false },
    { id: "database", title: "数据库", order: 3, completed: false, skippable: true },
    { id: "storage", title: "存储", order: 4, completed: false, skippable: true },
    { id: "finish", title: "完成", order: 99, completed: false, skippable: true },
  ]),
  currentStep: z.number().int().nonnegative().default(0),
});

export type OobeConfig = z.infer<typeof OobeConfigSchema>;
export type OobeSitePayload = z.infer<typeof OobeSitePayloadSchema>;
export type OobeAdminPayload = z.infer<typeof OobeAdminPayloadSchema>;
export type OobeDatabasePayload = z.infer<typeof OobeDatabasePayloadSchema>;
export type OobeStoragePayload = z.infer<typeof OobeStoragePayloadSchema>;
