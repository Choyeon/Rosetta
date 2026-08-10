import { z } from "zod";

export const SponsorTierSchema = z.object({
  id: z.string(),
  name: z.string(),
  amount: z.number().positive(),
  currency: z.string().default("CNY"),
  benefits: z.array(z.string()).default([]),
  color: z.string().optional(),
  featured: z.boolean().default(false),
});

export type SponsorTier = z.infer<typeof SponsorTierSchema>;

export const SponsorRecordSchema = z.object({
  id: z.string(),
  name: z.string(),
  amount: z.number().positive(),
  currency: z.string().default("CNY"),
  message: z.string().optional(),
  avatar: z.string().optional(),
  link: z.string().url().optional(),
  tierId: z.string().optional(),
  channel: z.enum(["wechat", "alipay", "paypal", "stripe", "kofi", "buymeacoffee", "custom"]).optional(),
  createdAt: z.string().datetime().optional(),
});

export type SponsorRecord = z.infer<typeof SponsorRecordSchema>;

export const SponsorConfigSchema = z.object({
  enabled: z.boolean().default(true),
  title: z.string().default("赞助本项目"),
  subtitle: z.string().default("如果 Rosetta 对你有帮助，欢迎请作者喝杯咖啡 ☕"),
  description: z.string().optional(),
  tiers: z.array(SponsorTierSchema).default([
    { id: "coffee", name: "请一杯咖啡", amount: 20, benefits: ["感谢名单留名"] },
    { id: "meal", name: "请一顿午餐", amount: 50, benefits: ["感谢名单留名", "专属徽章"] },
    { id: "featured", name: "特级赞助", amount: 200, benefits: ["感谢名单置顶", "专属徽章", "友链优先"], featured: true },
  ]),
  channels: z.object({
    wechat: z.object({ enabled: z.boolean().default(true), qrCode: z.string().optional() }).default({}),
    alipay: z.object({ enabled: z.boolean().default(true), qrCode: z.string().optional() }).default({}),
    paypal: z.object({ enabled: z.boolean().default(false), username: z.string().optional(), url: z.string().optional() }).default({}),
    kofi: z.object({ enabled: z.boolean().default(false), username: z.string().optional() }).default({}),
    buymeacoffee: z.object({ enabled: z.boolean().default(false), username: z.string().optional() }).default({}),
    custom: z.object({ enabled: z.boolean().default(false), label: z.string().optional(), url: z.string().optional() }).default({}),
  }).default({}),
  records: z.array(SponsorRecordSchema).default([]),
  showHistory: z.boolean().default(true),
  historyLimit: z.number().int().positive().default(50),
  showGoal: z.boolean().default(false),
  goalAmount: z.number().nonnegative().default(0),
  goalPeriod: z.enum(["monthly", "yearly", "total"]).default("total"),
  anonymousDefault: z.boolean().default(false),
  allowMessage: z.boolean().default(true),
  messageMaxLength: z.number().int().positive().default(200),
});

export type SponsorConfig = z.infer<typeof SponsorConfigSchema>;
