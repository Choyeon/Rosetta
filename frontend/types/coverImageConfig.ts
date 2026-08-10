import { z } from "zod";

export const CoverImageConfigSchema = z.object({
  enabled: z.boolean().default(true),
  mode: z.enum(["fixed", "random", "post-defined", "per-page"]).default("random"),
  defaultImage: z.string().default("/cover/default.jpg"),
  images: z.array(z.string()).default([]),
  aspectRatio: z.enum(["16:9", "21:9", "4:3", "1:1", "auto"]).default("16:9"),
  height: z.number().int().positive().optional(),
  minHeight: z.number().int().positive().default(300),
  maxHeight: z.number().int().positive().default(500),
  opacity: z.number().min(0).max(1).default(1),
  overlay: z.boolean().default(true),
  overlayColor: z.string().default("rgba(0,0,0,0.35)"),
  showTitle: z.boolean().default(true),
  showSubtitle: z.boolean().default(true),
  showMeta: z.boolean().default(true),
  parallax: z.boolean().default(false),
  parallaxSpeed: z.number().min(-1).max(1).default(0.2),
});

export type CoverImageConfig = z.infer<typeof CoverImageConfigSchema>;
