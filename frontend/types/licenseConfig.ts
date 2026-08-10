import { z } from "zod";

export const LicenseConfigSchema = z.object({
  enabled: z.boolean().default(true),
  type: z.enum([
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "CC-BY-ND-4.0",
    "CC-BY-NC-4.0",
    "CC-BY-NC-SA-4.0",
    "CC-BY-NC-ND-4.0",
    "CC0-1.0",
    "MIT",
    "GPL-3.0",
    "custom",
  ]).default("CC-BY-NC-SA-4.0"),
  name: z.string().default("署名-非商业性使用-相同方式共享 4.0 国际"),
  url: z.string().url().default("https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh"),
  icon: z.string().optional(),
  customText: z.string().optional(),
  showInArticles: z.boolean().default(true),
  showInFooter: z.boolean().default(false),
  showFullText: z.boolean().default(false),
  allowCommercial: z.boolean().default(false),
  allowDerivatives: z.boolean().default(true),
  requireAttribution: z.boolean().default(true),
  shareAlike: z.boolean().default(true),
});

export type LicenseConfig = z.infer<typeof LicenseConfigSchema>;
