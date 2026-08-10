import { z } from "zod";

export const BgSourceSchema = z.object({
  id: z.string(),
  type: z.enum(["local", "remote", "unsplash", "bing", "picsum", "gradient", "color"]).default("local"),
  src: z.string().default(""),
  opacity: z.number().min(0).max(1).default(1),
  brightness: z.number().min(0).max(2).default(1),
  blur: z.number().int().min(0).max(50).default(0),
  overlay: z.boolean().default(false),
  overlayColor: z.string().default("rgba(0,0,0,0.2)"),
});

export type BgSource = z.infer<typeof BgSourceSchema>;

export const BackgroundWallpaperConfigSchema = z.object({
  enabled: z.boolean().default(false),
  sources: z.array(BgSourceSchema).default([
    { id: "default", type: "color", src: "#0f172a" },
  ]),
  currentId: z.string().default("default"),
  rotation: z.enum(["none", "daily", "hourly", "session"]).default("none"),
  rotationPool: z.array(z.string()).default([]),
  unsplash: z.object({
    collections: z.array(z.string()).default([]),
    topics: z.array(z.string()).default([]),
    username: z.string().optional(),
    query: z.string().default("landscape"),
    orientation: z.enum(["landscape", "portrait", "squarish"]).default("landscape"),
    cacheTtlMs: z.number().int().positive().default(1000 * 60 * 60 * 6),
  }).default({}),
  bing: z.object({
    market: z.string().default("zh-CN"),
    cacheTtlMs: z.number().int().positive().default(1000 * 60 * 60 * 12),
  }).default({}),
  parallax: z.boolean().default(false),
  parallaxSpeed: z.number().min(-1).max(1).default(0.15),
  fixed: z.boolean().default(true),
  transition: z.enum(["fade", "slide", "none"]).default("fade"),
  transitionMs: z.number().int().positive().default(600),
  darkenOnDarkMode: z.boolean().default(true),
  maskOpacity: z.number().min(0).max(1).default(0.3),
});

export type BackgroundWallpaperConfig = z.infer<typeof BackgroundWallpaperConfigSchema>;
