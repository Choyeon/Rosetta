import { z } from "zod";

export const SidebarWidgetSchema = z.object({
  id: z.string(),
  enabled: z.boolean().default(true),
  order: z.number().int().default(0),
  collapsed: z.boolean().default(false),
});

export const SidebarConfigSchema = z.object({
  position: z.enum(["left", "right", "both"]).default("right"),
  width: z.number().int().positive().default(300),
  sticky: z.boolean().default(true),
  showOnMobile: z.boolean().default(false),
  widgets: z.array(SidebarWidgetSchema).default([
    { id: "profile", enabled: true, order: 0, collapsed: false },
    { id: "toc", enabled: true, order: 1, collapsed: false },
    { id: "category", enabled: true, order: 2, collapsed: false },
    { id: "tagcloud", enabled: true, order: 3, collapsed: false },
    { id: "recent", enabled: true, order: 4, collapsed: false },
    { id: "archive", enabled: true, order: 5, collapsed: true },
  ]),
  profileCard: z.object({
    showAvatar: z.boolean().default(true),
    showBadges: z.boolean().default(true),
    showStats: z.boolean().default(true),
  }).default({}),
  tocCard: z.object({
    depth: z.number().int().min(1).max(6).default(3),
    numbered: z.boolean().default(false),
  }).default({}),
});

export type SidebarWidget = z.infer<typeof SidebarWidgetSchema>;
export type SidebarConfig = z.infer<typeof SidebarConfigSchema>;
