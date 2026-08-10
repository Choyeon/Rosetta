import { z } from "zod";

export const FriendLinkSchema = z.object({
  id: z.string(),
  name: z.string(),
  url: z.string().url(),
  avatar: z.string().optional(),
  description: z.string().optional(),
  category: z.string().default("default"),
  group: z.string().optional(),
  order: z.number().int().default(0),
  approved: z.boolean().default(true),
  createdAt: z.string().datetime().optional(),
  updatedAt: z.string().datetime().optional(),
});

export type FriendLink = z.infer<typeof FriendLinkSchema>;

export const FriendsConfigSchema = z.object({
  enabled: z.boolean().default(true),
  title: z.string().default("友情链接"),
  subtitle: z.string().optional(),
  description: z.string().optional(),
  allowApply: z.boolean().default(true),
  requireApproval: z.boolean().default(true),
  applyForm: z.object({
    requireAvatar: z.boolean().default(false),
    requireDescription: z.boolean().default(true),
    requireEmail: z.boolean().default(false),
  }).default({}),
  groups: z.array(z.object({
    id: z.string(),
    name: z.string(),
    order: z.number().int().default(0),
  })).default([]),
  layout: z.enum(["card", "list", "grid"]).default("card"),
  columns: z.number().int().min(1).max(6).default(3),
  showAvatar: z.boolean().default(true),
  showDescription: z.boolean().default(true),
  links: z.array(FriendLinkSchema).default([]),
  siteInfo: z.object({
    name: z.string().default("Rosetta"),
    url: z.string().default("http://localhost:3000"),
    avatar: z.string().default("/avatar.png"),
    description: z.string().default("轻羽博客系统"),
  }).default({}),
});

export type FriendsConfig = z.infer<typeof FriendsConfigSchema>;
