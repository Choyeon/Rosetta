export { default as siteConfig } from "./siteConfig";
export { default as profileConfig } from "./profileConfig";
export { default as sidebarConfig } from "./sidebarConfig";
export { default as footerConfig } from "./footerConfig";
export { default as navBarConfig } from "./navBarConfig";
export { default as coverImageConfig } from "./coverImageConfig";
export { default as commentConfig } from "./commentConfig";
export { default as analyticsConfig } from "./analyticsConfig";
export { default as musicConfig } from "./musicConfig";
export { default as effectsConfig } from "./effectsConfig";
export { default as displaySettingsConfig } from "./displaySettingsConfig";
export { default as fontConfig } from "./fontConfig";
export { default as galleryConfig } from "./galleryConfig";
export { default as friendsConfig } from "./friendsConfig";
export { default as licenseConfig } from "./licenseConfig";
export { default as pioConfig } from "./pioConfig";
export { default as sponsorConfig } from "./sponsorConfig";
export { default as announcementConfig } from "./announcementConfig";
export { default as dynamicConfig } from "./dynamicConfig";
export { default as mermaidConfig } from "./mermaidConfig";
export { default as plantumlConfig } from "./plantumlConfig";
export { default as backgroundWallpaper } from "./backgroundWallpaper";
export { default as bangumi } from "./bangumi";
export { default as anime } from "./anime";
export { default as appConfig } from "./config";
export { default as oobe } from "./oobe";

import siteConfig from "./siteConfig";
import profileConfig from "./profileConfig";
import sidebarConfig from "./sidebarConfig";
import footerConfig from "./footerConfig";
import navBarConfig from "./navBarConfig";
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
import appConfig from "./config";
import oobe from "./oobe";

export const allConfigs = {
  siteConfig,
  profileConfig,
  sidebarConfig,
  footerConfig,
  navBarConfig,
  coverImageConfig,
  commentConfig,
  analyticsConfig,
  musicConfig,
  effectsConfig,
  displaySettingsConfig,
  fontConfig,
  galleryConfig,
  friendsConfig,
  licenseConfig,
  pioConfig,
  sponsorConfig,
  announcementConfig,
  dynamicConfig,
  mermaidConfig,
  plantumlConfig,
  backgroundWallpaper,
  bangumi,
  anime,
  appConfig,
  oobe,
} as const;
