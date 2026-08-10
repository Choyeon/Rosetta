import { z } from "zod";

export const PioModelSchema = z.object({
  id: z.string(),
  name: z.string(),
  base: z.string().url(),
  costume: z.string().default("default"),
  className: z.string().default("pio-container"),
  width: z.number().int().positive().default(200),
  height: z.number().int().positive().default(300),
});

export const PioDialogSchema = z.object({
  welcome: z.array(z.string()).default(["欢迎来到 Rosetta！"]),
  goodbye: z.array(z.string()).default(["下次再见~"]),
  idle: z.array(z.string()).default(["在发呆呢..."]),
  hint: z.object({
    copy: z.array(z.string()).default(["检测到复制内容，记得注明出处哦！"]),
    visibility: z.array(z.string()).default(["不在看我了吗？"]),
    referrer: z.record(z.string(), z.array(z.string())).default({}),
  }).default({}),
});

export const PioConfigSchema = z.object({
  enabled: z.boolean().default(false),
  position: z.enum(["bottom-left", "bottom-right"]).default("bottom-left"),
  mobile: z.boolean().default(false),
  models: z.array(PioModelSchema).default([
    { id: "shizuku", name: "Shizuku", base: "https://cdn.jsdelivr.net/gh/FghrPro/Live2D-Waifu@0.1.8/models/shizuku/", costume: "default" },
  ]),
  currentModelId: z.string().default("shizuku"),
  dialog: PioDialogSchema.default({}),
  interactive: z.object({
    canHover: z.boolean().default(true),
    canClick: z.boolean().default(true),
    canDrag: z.boolean().default(true),
    showHitokoto: z.boolean().default(true),
    showClock: z.boolean().default(false),
    showWeather: z.boolean().default(false),
  }).default({}),
  tools: z.object({
    camera: z.boolean().default(true),
    screenshot: z.boolean().default(false),
    switch: z.boolean().default(true),
    home: z.boolean().default(true),
    comment: z.boolean().default(true),
    quit: z.boolean().default(true),
  }).default({}),
  opacity: z.number().min(0).max(1).default(1),
  zIndex: z.number().int().default(1000),
});

export type PioConfig = z.infer<typeof PioConfigSchema>;
