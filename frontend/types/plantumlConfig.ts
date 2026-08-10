import { z } from "zod";

export const PlantumlConfigSchema = z.object({
  enabled: z.boolean().default(false),
  renderServer: z.enum(["plantuml.com", "local", "custom"]).default("plantuml.com"),
  customServer: z.string().url().optional(),
  format: z.enum(["svg", "png", "txt"]).default("svg"),
  skinParam: z.object({
    monochrome: z.boolean().default(false),
    shadowing: z.boolean().default(true),
    handwritten: z.boolean().default(false),
    backgroundColor: z.string().optional(),
    borderColor: z.string().optional(),
    arrowColor: z.string().optional(),
    fontSize: z.number().int().positive().optional(),
  }).default({}),
  fallbackImage: z.string().optional(),
  lazyLoad: z.boolean().default(true),
  inlineSvg: z.boolean().default(true),
  cacheBust: z.boolean().default(false),
  deflate: z.enum(["deflate", "none"]).default("deflate"),
});

export type PlantumlConfig = z.infer<typeof PlantumlConfigSchema>;
