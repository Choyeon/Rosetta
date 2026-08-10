import { z } from "zod";

export const DisplaySettingsConfigSchema = z.object({
  theme: z.enum(["light", "dark", "system"]).default("system"),
  primaryColor: z.string().default("#6366f1"),
  accentColor: z.string().default("#ec4899"),
  radius: z.enum(["none", "sm", "md", "lg", "xl", "2xl", "3xl", "full"]).default("lg"),
  fontScale: z.number().min(0.8).max(1.4).default(1),
  compact: z.boolean().default(false),
  dense: z.boolean().default(false),
  reduceMotion: z.boolean().default(false),
  reducedTransparency: z.boolean().default(false),
  highContrast: z.boolean().default(false),
  readingWidthMax: z.number().int().positive().default(780),
  showBreadcrumb: z.boolean().default(true),
  showTableOfContents: z.boolean().default(true),
  showSidebar: z.boolean().default(true),
  sidebarPanelCollapsed: z.boolean().default(false),
  rightPanelCollapsed: z.boolean().default(false),
  cardHover: z.boolean().default(true),
  imageLazy: z.boolean().default(true),
  imagePlaceholder: z.boolean().default(true),
});

export type DisplaySettingsConfig = z.infer<typeof DisplaySettingsConfigSchema>;
