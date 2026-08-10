import { z } from "zod";

export const BangumiSubjectSchema = z.object({
  id: z.string(),
  subjectId: z.string(),
  title: z.string(),
  originalTitle: z.string().optional(),
  cover: z.string().optional(),
  type: z.enum(["anime", "movie", "tv", "ova", "ona", "other"]).default("anime"),
  status: z.enum(["watching", "watched", "planned", "on-hold", "dropped"]).default("watching"),
  progress: z.number().int().nonnegative().default(0),
  totalEpisodes: z.number().int().positive().default(12),
  score: z.number().min(0).max(10).default(0),
  userScore: z.number().min(0).max(10).optional(),
  summary: z.string().optional(),
  startDate: z.string().date().optional(),
  endDate: z.string().date().optional(),
  tags: z.array(z.string()).default([]),
  source: z.enum(["bilibili", "bangumi-tv", "manual"]).default("manual"),
  sourceUrl: z.string().url().optional(),
  lastUpdatedAt: z.string().datetime().optional(),
});

export type BangumiSubject = z.infer<typeof BangumiSubjectSchema>;

export const BangumiConfigSchema = z.object({
  enabled: z.boolean().default(true),
  title: z.string().default("追番"),
  subtitle: z.string().optional(),
  layout: z.enum(["grid", "list", "timeline"]).default("grid"),
  columns: z.number().int().min(1).max(6).default(4),
  showScore: z.boolean().default(true),
  showProgress: z.boolean().default(true),
  showTags: z.boolean().default(true),
  showTotalCount: z.boolean().default(true),
  showSeasonSelector: z.boolean().default(true),
  statusFilters: z.array(z.enum(["watching", "watched", "planned", "on-hold", "dropped"])).default(["watching", "planned"]),
  items: z.array(BangumiSubjectSchema).default([]),
  providers: z.object({
    bilibili: z.object({
      enabled: z.boolean().default(false),
      uid: z.string().default(""),
      autoSync: z.boolean().default(false),
    }).default({}),
    bangumi: z.object({
      enabled: z.boolean().default(false),
      username: z.string().default(""),
      autoSync: z.boolean().default(false),
    }).default({}),
  }).default({}),
});

export type BangumiConfig = z.infer<typeof BangumiConfigSchema>;
