import { z } from "zod";

export const CommentProviderGiscusSchema = z.object({
  provider: z.literal("giscus"),
  repo: z.string(),
  repoId: z.string(),
  category: z.string(),
  categoryId: z.string(),
  mapping: z.enum(["pathname", "url", "title", "og:title", "specific", "number"]).default("pathname"),
  strict: z.boolean().default(false),
  reactionsEnabled: z.enum(["1", "0"]).default("1"),
  emitMetadata: z.enum(["1", "0"]).default("0"),
  inputPosition: z.enum(["top", "bottom"]).default("bottom"),
  theme: z.string().default("preferred_color_scheme"),
  lang: z.string().default("zh-CN"),
});

export const CommentProviderWalineSchema = z.object({
  provider: z.literal("waline"),
  serverURL: z.string().url(),
  lang: z.string().default("zh-CN"),
  dark: z.string().default("auto"),
  emoji: z.array(z.string()).default(["https://unpkg.com/@waline/emojis@1.2.0/weibo"]),
  meta: z.array(z.enum(["nick", "mail", "link"])).default(["nick", "mail", "link"]),
  requiredMeta: z.array(z.enum(["nick", "mail", "link"])).default([]),
  login: z.enum(["force", "enable", "disable"]).default("enable"),
  wordLimit: z.number().int().default(0),
  pageSize: z.number().int().positive().default(10),
  avatarCDN: z.string().default("https://www.gravatar.com/avatar/"),
});

export const CommentProviderTwikooSchema = z.object({
  provider: z.literal("twikoo"),
  envId: z.string(),
  region: z.string().default("ap-shanghai"),
  lang: z.string().default("zh-CN"),
});

export const CommentProviderArtalkSchema = z.object({
  provider: z.literal("artalk"),
  server: z.string().url(),
  site: z.string(),
  placeholder: z.string().optional(),
  noComment: z.string().optional(),
  flatMode: z.boolean().default(false),
  maxNesting: z.number().int().default(3),
  pageSize: z.number().int().default(20),
  readMore: z.number().int().default(0),
  avatar: z.enum(["mp", "identicon", "monsterid", "wavatar", "retro", "robohash", "hide"]).default("mp"),
  gravatar: z.object({
    cdn: z.string().default("https://www.gravatar.com/avatar/"),
    mirror: z.string().default("cn.gravatar.com"),
  }).default({}),
});

export const CommentProviderBuiltinSchema = z.object({
  provider: z.literal("builtin"),
  allowGuest: z.boolean().default(true),
  requireApproval: z.boolean().default(true),
  maxLength: z.number().int().positive().default(2000),
  pageSize: z.number().int().positive().default(10),
  enableMarkdown: z.boolean().default(true),
  enableMention: z.boolean().default(true),
});

export const CommentProviderSchema = z.discriminatedUnion("provider", [
  CommentProviderGiscusSchema,
  CommentProviderWalineSchema,
  CommentProviderTwikooSchema,
  CommentProviderArtalkSchema,
  CommentProviderBuiltinSchema,
]);

export type CommentProvider = z.infer<typeof CommentProviderSchema>;

export const CommentConfigSchema = z.object({
  enabled: z.boolean().default(true),
  provider: CommentProviderSchema.default({ provider: "builtin" }),
  showCount: z.boolean().default(true),
  showLikes: z.boolean().default(true),
  showReactions: z.boolean().default(true),
  showShare: z.boolean().default(true),
  allowAnonymous: z.boolean().default(true),
  antiSpam: z.boolean().default(true),
  rateLimitMs: z.number().int().nonnegative().default(5000),
});

export type CommentConfig = z.infer<typeof CommentConfigSchema>;
