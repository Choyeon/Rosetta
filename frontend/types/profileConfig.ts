import { z } from "zod";

export const SocialLinkSchema = z.object({
  platform: z.string(),
  url: z.string().url(),
  icon: z.string().optional(),
  label: z.string().optional(),
});

export const ProfileConfigSchema = z.object({
  avatar: z.string().default("/avatar.png"),
  nickname: z.string().default("Rosetta Admin"),
  bio: z.string().default("热爱技术与分享"),
  title: z.string().optional(),
  company: z.string().optional(),
  location: z.string().optional(),
  email: z.string().email().optional(),
  links: z.array(SocialLinkSchema).default([]),
  statusText: z.string().default("在线摸鱼中~"),
  statusEmoji: z.string().default("🐟"),
  showReadingStats: z.boolean().default(true),
  showVisitorMap: z.boolean().default(false),
});

export type SocialLink = z.infer<typeof SocialLinkSchema>;
export type ProfileConfig = z.infer<typeof ProfileConfigSchema>;
