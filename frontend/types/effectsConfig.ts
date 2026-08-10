import { z } from "zod";

export const CursorEffectSchema = z.object({
  enabled: z.boolean().default(false),
  type: z.enum(["none", "trail", "particles", "ripple", "emoji", "fireworks"]).default("trail"),
  color: z.string().default("#6366f1"),
  size: z.number().min(1).max(50).default(8),
  opacity: z.number().min(0).max(1).default(0.6),
  lifetimeMs: z.number().int().positive().default(800),
  particleCount: z.number().int().min(1).max(50).default(20),
});

export const CanvasEffectSchema = z.object({
  enabled: z.boolean().default(false),
  type: z.enum(["none", "particles", "nest", "stars", "wave", "sakura", "matrix", "confetti"]).default("particles"),
  zIndex: z.number().int().default(-1),
  opacity: z.number().min(0).max(1).default(0.3),
  color: z.string().default("#6366f1"),
  density: z.number().min(0.1).max(10).default(1),
  speed: z.number().min(0.1).max(5).default(1),
});

export const BackgroundEffectSchema = z.object({
  enabled: z.boolean().default(false),
  gradient: z.boolean().default(true),
  gradientColors: z.array(z.string()).default(["#667eea", "#764ba2"]),
  gradientAngle: z.number().int().min(0).max(360).default(135),
  animation: z.boolean().default(false),
  animationDurationMs: z.number().int().positive().default(15000),
});

export const ReadingProgressSchema = z.object({
  enabled: z.boolean().default(true),
  position: z.enum(["top", "bottom", "left", "right"]).default("top"),
  color: z.string().default("#6366f1"),
  height: z.number().int().positive().default(3),
  opacity: z.number().min(0).max(1).default(0.9),
});

export const EffectsConfigSchema = z.object({
  cursor: CursorEffectSchema.default({}),
  canvas: CanvasEffectSchema.default({}),
  background: BackgroundEffectSchema.default({}),
  readingProgress: ReadingProgressSchema.default({}),
  enableSnow: z.boolean().default(false),
  enableCherryBlossom: z.boolean().default(false),
  enableFireworksOnClick: z.boolean().default(false),
  pageTransition: z.boolean().default(true),
  smoothScroll: z.boolean().default(true),
});

export type EffectsConfig = z.infer<typeof EffectsConfigSchema>;
