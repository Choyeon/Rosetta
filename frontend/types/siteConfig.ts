import { z } from "zod";

export const SiteConfigSchema = z.object({
  name: z.string().min(1).default("Rosetta"),
  subtitle: z.string().default("轻羽博客系统"),
  description: z.string().default("以内容与体验为核心的现代化博客系统"),
  keywords: z.array(z.string()).default([]),
  logo: z.string().optional(),
  favicon: z.string().optional(),
  url: z.string().url().default("http://localhost:3000"),
  locale: z.enum(["zh-CN", "zh-TW", "en", "ja"]).default("zh-CN"),
  timezone: z.string().default("Asia/Shanghai"),
  copyright: z.string().optional(),
  icp: z.string().optional(),
  policeRecord: z.string().optional(),
  footerText: z.string().optional(),
});

export type SiteConfig = z.infer<typeof SiteConfigSchema>;
