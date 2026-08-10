import { AppConfigSchema, type AppConfig } from "../types/config";
import siteConfig from "./siteConfig";
import profileConfig from "./profileConfig";
import navBarConfig from "./navBarConfig";
import sidebarConfig from "./sidebarConfig";
import footerConfig from "./footerConfig";
import coverImageConfig from "./coverImageConfig";
import commentConfig from "./commentConfig";
import analyticsConfig from "./analyticsConfig";
import musicConfig from "./musicConfig";
import effectsConfig from "./effectsConfig";
import displaySettingsConfig from "./displaySettingsConfig";
import fontConfig from "./fontConfig";
import galleryConfig from "./galleryConfig";
import friendsConfig from "./friendsConfig";
import licenseConfig from "./licenseConfig";
import pioConfig from "./pioConfig";
import sponsorConfig from "./sponsorConfig";
import announcementConfig from "./announcementConfig";
import dynamicConfig from "./dynamicConfig";
import mermaidConfig from "./mermaidConfig";
import plantumlConfig from "./plantumlConfig";
import backgroundWallpaper from "./backgroundWallpaper";
import bangumi from "./bangumi";
import anime from "./anime";

const raw: Partial<AppConfig> = {
  site: siteConfig,
  profile: profileConfig,
  navBar: navBarConfig,
  sidebar: sidebarConfig,
  footer: footerConfig,
  coverImage: coverImageConfig,
  comment: commentConfig,
  analytics: analyticsConfig,
  music: musicConfig,
  effects: effectsConfig,
  display: displaySettingsConfig,
  font: fontConfig,
  gallery: galleryConfig,
  friends: friendsConfig,
  license: licenseConfig,
  pio: pioConfig,
  sponsor: sponsorConfig,
  announcement: announcementConfig,
  dynamic: dynamicConfig,
  mermaid: mermaidConfig,
  plantuml: plantumlConfig,
  backgroundWallpaper,
  bangumi,
  anime,
};

const result = AppConfigSchema.safeParse(raw);
if (!result.success) {
  console.warn("[config/config] AppConfig schema 校验失败，使用默认值兜底:", result.error.issues);
}

const appConfig: AppConfig = result.success ? result.data : AppConfigSchema.parse({});

export default appConfig;
