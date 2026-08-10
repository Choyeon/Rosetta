import { z } from "zod";

export const FontFallbackSchema = z.array(z.string()).default([
  "-apple-system",
  "BlinkMacSystemFont",
  "Segoe UI",
  "Roboto",
  "Helvetica Neue",
  "Arial",
  "sans-serif",
]);

export const FontConfigSchema = z.object({
  baseSize: z.number().int().positive().default(16),
  baseLineHeight: z.number().min(1).max(2.5).default(1.6),
  headingLineHeight: z.number().min(1).max(2).default(1.3),
  sans: z.object({
    family: z.string().default("Inter"),
    fallbacks: FontFallbackSchema,
    weights: z.array(z.number().int()).default([300, 400, 500, 600, 700]),
    subset: z.string().default("latin"),
    display: z.enum(["auto", "block", "swap", "fallback", "optional"]).default("swap"),
    variable: z.boolean().default(true),
  }).default({}),
  serif: z.object({
    family: z.string().default("Noto Serif SC"),
    fallbacks: z.array(z.string()).default(["Georgia", "Cambria", "Times New Roman", "serif"]),
    weights: z.array(z.number().int()).default([400, 500, 600, 700]),
  }).default({}),
  mono: z.object({
    family: z.string().default("JetBrains Mono"),
    fallbacks: z.array(z.string()).default(["SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"]),
    weights: z.array(z.number().int()).default([400, 500, 600, 700]),
    ligatures: z.boolean().default(true),
  }).default({}),
  cjk: z.object({
    family: z.string().default("Noto Sans SC"),
    fallbacks: z.array(z.string()).default(["PingFang SC", "Microsoft YaHei", "WenQuanYi Micro Hei", "sans-serif"]),
    weights: z.array(z.number().int()).default([300, 400, 500, 600, 700]),
    subset: z.string().default("chinese-simplified"),
  }).default({}),
  icon: z.object({
    provider: z.string().default("iconify"),
    collections: z.array(z.string()).default(["material-symbols", "fa7-solid", "mdi"]),
  }).default({}),
  loadStrategy: z.enum(["preload", "async", "defer"]).default("async"),
});

export type FontConfig = z.infer<typeof FontConfigSchema>;
