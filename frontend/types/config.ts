import { z } from "zod";
import { SiteConfigSchema } from "./siteConfig";
import { ProfileConfigSchema } from "./profileConfig";
import { SidebarConfigSchema } from "./sidebarConfig";
import { FooterConfigSchema } from "./footerConfig";
import { NavBarConfigSchema } from "./navBarConfig";
import { CoverImageConfigSchema } from "./coverImageConfig";
import { CommentConfigSchema } from "./commentConfig";
import { AnalyticsConfigSchema } from "./analyticsConfig";
import { MusicConfigSchema } from "./musicConfig";
import { EffectsConfigSchema } from "./effectsConfig";
import { DisplaySettingsConfigSchema } from "./displaySettingsConfig";
import { FontConfigSchema } from "./fontConfig";
import { GalleryConfigSchema } from "./galleryConfig";
import { FriendsConfigSchema } from "./friendsConfig";
import { LicenseConfigSchema } from "./licenseConfig";
import { PioConfigSchema } from "./pioConfig";
import { SponsorConfigSchema } from "./sponsorConfig";
import { AnnouncementConfigSchema } from "./announcementConfig";
import { DynamicConfigSchema } from "./dynamicConfig";
import { MermaidConfigSchema } from "./mermaidConfig";
import { PlantumlConfigSchema } from "./plantumlConfig";
import { BackgroundWallpaperConfigSchema } from "./backgroundWallpaper";
import { BangumiConfigSchema } from "./bangumi";
import { AnimeConfigSchema } from "./anime";

export const AppConfigSchema = z.object({
  site: SiteConfigSchema,
  profile: ProfileConfigSchema,
  navBar: NavBarConfigSchema,
  sidebar: SidebarConfigSchema,
  footer: FooterConfigSchema,
  coverImage: CoverImageConfigSchema,
  comment: CommentConfigSchema,
  analytics: AnalyticsConfigSchema,
  music: MusicConfigSchema,
  effects: EffectsConfigSchema,
  display: DisplaySettingsConfigSchema,
  font: FontConfigSchema,
  gallery: GalleryConfigSchema,
  friends: FriendsConfigSchema,
  license: LicenseConfigSchema,
  pio: PioConfigSchema,
  sponsor: SponsorConfigSchema,
  announcement: AnnouncementConfigSchema,
  dynamic: DynamicConfigSchema,
  mermaid: MermaidConfigSchema,
  plantuml: PlantumlConfigSchema,
  backgroundWallpaper: BackgroundWallpaperConfigSchema,
  bangumi: BangumiConfigSchema,
  anime: AnimeConfigSchema,
  version: z.string().default("2.0.0"),
  schemaVersion: z.number().int().positive().default(1),
  updatedAt: z.string().datetime().optional(),
});

export type AppConfig = z.infer<typeof AppConfigSchema>;
