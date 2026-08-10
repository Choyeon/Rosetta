import { z } from "zod";

export const NavItemSchema = z.object({
  id: z.string(),
  label: z.string(),
  href: z.string().default("/"),
  icon: z.string().optional(),
  children: z.lazy(() => z.array(NavItemSchema)).optional(),
  external: z.boolean().default(false),
  target: z.enum(["_self", "_blank", "_parent", "_top"]).default("_self"),
  enabled: z.boolean().default(true),
  order: z.number().int().default(0),
});

export type NavItem = z.infer<typeof NavItemSchema>;

export const NavBarConfigSchema = z.object({
  enabled: z.boolean().default(true),
  fixed: z.boolean().default(true),
  transparent: z.boolean().default(false),
  showLogo: z.boolean().default(true),
  showSearch: z.boolean().default(true),
  showColorMode: z.boolean().default(true),
  showLocaleSwitcher: z.boolean().default(true),
  showMobileMenu: z.boolean().default(true),
  items: z.array(NavItemSchema).default([]),
  height: z.number().int().positive().default(64),
  blurOnScroll: z.boolean().default(true),
  shadow: z.boolean().default(true),
});

export type NavBarConfig = z.infer<typeof NavBarConfigSchema>;
