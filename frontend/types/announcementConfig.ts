import { z } from "zod";

export const AnnouncementSchema = z.object({
  id: z.string(),
  kind: z.enum(["top-bar", "banner", "modal", "toast"]).default("top-bar"),
  title: z.string().optional(),
  content: z.string().default(""),
  cta: z.object({ label: z.string(), href: z.string() }).optional(),
  tone: z.enum(["info", "warning", "success", "danger"]).default("info"),
  dismissable: z.boolean().default(true),
  autoHideMs: z.number().int().nonnegative().default(0),
  frequency: z.enum(["always", "once", "session"]).default("session"),
  startAt: z.string().datetime().optional(),
  endAt: z.string().datetime().optional(),
  includePaths: z.array(z.string()).default([]),
  excludePaths: z.array(z.string()).default([]),
  priority: z.number().int().default(0),
  active: z.boolean().default(true),
});

export type Announcement = z.infer<typeof AnnouncementSchema>;

export const AnnouncementConfigSchema = z.object({
  enabled: z.boolean().default(true),
  items: z.array(AnnouncementSchema).default([]),
  topBar: z.object({
    height: z.number().int().positive().default(36),
    sticky: z.boolean().default(true),
    pushContent: z.boolean().default(true),
  }).default({}),
  modal: z.object({
    showOverlay: z.boolean().default(true),
    closeOnClickOutside: z.boolean().default(true),
  }).default({}),
  toast: z.object({
    position: z.enum(["top-left", "top-right", "bottom-left", "bottom-right", "top-center", "bottom-center"]).default("top-right"),
    durationMs: z.number().int().positive().default(4000),
    maxVisible: z.number().int().positive().default(3),
  }).default({}),
});

export type AnnouncementConfig = z.infer<typeof AnnouncementConfigSchema>;
