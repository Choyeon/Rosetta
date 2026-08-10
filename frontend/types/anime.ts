import { z } from "zod";

export const AnimeEpisodeSchema = z.object({
  id: z.string(),
  number: z.number().int().positive(),
  title: z.string().optional(),
  durationSec: z.number().int().positive().optional(),
  airedAt: z.string().datetime().optional(),
  watched: z.boolean().default(false),
  progress: z.number().min(0).max(1).default(0),
  thumbnail: z.string().optional(),
});

export type AnimeEpisode = z.infer<typeof AnimeEpisodeSchema>;

export const AnimeItemSchema = z.object({
  id: z.string(),
  malId: z.string().optional(),
  anilistId: z.string().optional(),
  title: z.string(),
  titleEn: z.string().optional(),
  titleJp: z.string().optional(),
  cover: z.string().optional(),
  banner: z.string().optional(),
  type: z.enum(["tv", "movie", "ova", "ona", "special", "music"]).default("tv"),
  status: z.enum(["airing", "finished", "not-yet-aired"]).default("airing"),
  userStatus: z.enum(["watching", "completed", "plan-to-watch", "on-hold", "dropped"]).default("plan-to-watch"),
  episodes: z.array(AnimeEpisodeSchema).default([]),
  totalEpisodes: z.number().int().positive().default(12),
  season: z.enum(["winter", "spring", "summer", "fall"]).optional(),
  year: z.number().int().positive().optional(),
  score: z.number().min(0).max(10).optional(),
  userScore: z.number().min(0).max(10).optional(),
  synopsis: z.string().optional(),
  genres: z.array(z.string()).default([]),
  studios: z.array(z.string()).default([]),
  startDate: z.string().date().optional(),
  endDate: z.string().date().optional(),
  watchedDate: z.string().date().optional(),
  source: z.enum(["manual", "anilist", "myanimelist"]).default("manual"),
});

export type AnimeItem = z.infer<typeof AnimeItemSchema>;

export const AnimeConfigSchema = z.object({
  enabled: z.boolean().default(true),
  title: z.string().default("番剧"),
  subtitle: z.string().optional(),
  layout: z.enum(["grid", "list", "season"]).default("season"),
  seasonColumns: z.number().int().min(1).max(6).default(3),
  showSeasonBanner: z.boolean().default(true),
  showAiringStatus: z.boolean().default(true),
  showEpisodeList: z.boolean().default(true),
  groupBySeason: z.boolean().default(true),
  currentSeason: z.enum(["auto", "winter", "spring", "summer", "fall"]).default("auto"),
  sortBy: z.enum(["score", "year", "title", "user"]).default("score"),
  items: z.array(AnimeItemSchema).default([]),
  providers: z.object({
    anilist: z.object({
      enabled: z.boolean().default(false),
      username: z.string().default(""),
      autoSync: z.boolean().default(false),
    }).default({}),
    mal: z.object({
      enabled: z.boolean().default(false),
      username: z.string().default(""),
      autoSync: z.boolean().default(false),
    }).default({}),
  }).default({}),
});

export type AnimeConfig = z.infer<typeof AnimeConfigSchema>;
