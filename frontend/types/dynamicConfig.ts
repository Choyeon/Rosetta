import { z } from "zod";

export const DynamicItemMediaSchema = z.object({
  id: z.string(),
  type: z.enum(["image", "video", "audio", "link"]).default("image"),
  url: z.string().url(),
  thumbnail: z.string().optional(),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
  title: z.string().optional(),
  alt: z.string().optional(),
});

export const DynamicItemSchema = z.object({
  id: z.string(),
  slug: z.string(),
  content: z.string(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime().optional(),
  pinned: z.boolean().default(false),
  private: z.boolean().default(false),
  media: z.array(DynamicItemMediaSchema).default([]),
  tags: z.array(z.string()).default([]),
  likes: z.number().int().nonnegative().default(0),
  comments: z.number().int().nonnegative().default(0),
  views: z.number().int().nonnegative().default(0),
  location: z.object({ name: z.string(), lat: z.number().optional(), lng: z.number().optional() }).optional(),
  mood: z.string().optional(),
  weather: z.string().optional(),
  source: z.enum(["builtin", "memos", "custom"]).default("builtin"),
  sourceRef: z.string().optional(),
});

export type DynamicItem = z.infer<typeof DynamicItemSchema>;

export const DynamicConfigSchema = z.object({
  enabled: z.boolean().default(true),
  pageSize: z.number().int().positive().default(20),
  reverseOrder: z.boolean().default(true),
  showMedia: z.boolean().default(true),
  showDate: z.boolean().default(true),
  showTags: z.boolean().default(true),
  showLikes: z.boolean().default(true),
  showComments: z.boolean().default(true),
  showPinnedFirst: z.boolean().default(true),
  allowComments: z.boolean().default(true),
  allowLikes: z.boolean().default(true),
  allowSharing: z.boolean().default(true),
  embedYoutube: z.boolean().default(true),
  embedBilibili: z.boolean().default(true),
  embedSpotify: z.boolean().default(false),
  formatDateAsRelative: z.boolean().default(true),
  markdown: z.boolean().default(true),
  maxLength: z.number().int().positive().default(500),
  items: z.array(DynamicItemSchema).default([]),
  memos: z.object({
    enabled: z.boolean().default(false),
    api: z.string().url().default(""),
    token: z.string().default(""),
    creatorId: z.string().optional(),
    autoSync: z.boolean().default(false),
    syncIntervalMs: z.number().int().positive().default(1000 * 60 * 30),
  }).default({}),
});

export type DynamicConfig = z.infer<typeof DynamicConfigSchema>;
