import { z } from "zod";

export const FooterLinkGroupSchema = z.object({
  title: z.string(),
  links: z.array(z.object({
    label: z.string(),
    href: z.string(),
    external: z.boolean().default(false),
  })),
});

export const FooterConfigSchema = z.object({
  enabled: z.boolean().default(true),
  groups: z.array(FooterLinkGroupSchema).default([]),
  showCopyright: z.boolean().default(true),
  showPoweredBy: z.boolean().default(true),
  showThemeInfo: z.boolean().default(false),
  showICP: z.boolean().default(true),
  showSocialIcons: z.boolean().default(true),
  background: z.string().optional(),
  textAlign: z.enum(["left", "center", "right"]).default("center"),
});

export type FooterLinkGroup = z.infer<typeof FooterLinkGroupSchema>;
export type FooterConfig = z.infer<typeof FooterConfigSchema>;
