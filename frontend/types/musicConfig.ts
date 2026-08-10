import { z } from "zod";

export const MusicTrackSchema = z.object({
  id: z.string(),
  name: z.string(),
  artist: z.string(),
  album: z.string().optional(),
  cover: z.string().url().optional(),
  url: z.string().url().optional(),
  lrc: z.string().optional(),
});

export type MusicTrack = z.infer<typeof MusicTrackSchema>;

export const MusicMetingConfigSchema = z.object({
  enabled: z.boolean().default(false),
  server: z.enum(["netease", "tencent", "kugou", "kuwo", "baidu", "migu", "xiami", "youtube", "bilibili"]).default("netease"),
  type: z.enum(["song", "playlist", "album", "search", "artist"]).default("playlist"),
  id: z.string().default(""),
});

export const MusicConfigSchema = z.object({
  enabled: z.boolean().default(false),
  position: z.enum(["bottom-left", "bottom-right", "top-right", "top-left"]).default("bottom-right"),
  mode: z.enum(["mini", "full"]).default("mini"),
  autoPlay: z.boolean().default(false),
  volume: z.number().min(0).max(1).default(0.6),
  loop: z.enum(["none", "one", "all"]).default("all"),
  showLrc: z.boolean().default(false),
  themeColor: z.string().default("#6366f1"),
  tracks: z.array(MusicTrackSchema).default([]),
  meting: MusicMetingConfigSchema.default({}),
});

export type MusicConfig = z.infer<typeof MusicConfigSchema>;
