/// <reference types="astro/client" />
/// <reference path="../.astro/types.d.ts" />

// 通过 astro.config.mjs 中 vite.define 注入的构建时全局常量：
// 直接使用 __ROSETTA_PKG_VERSION__ 获取当前项目版本号（如 "2.0.0"）
declare const __ROSETTA_PKG_VERSION__: string | undefined;

declare global {
	interface ImportMetaEnv {
		readonly MEILI_MASTER_KEY: string;
	}

	interface ITOCManager {
		init: () => void;
		render: () => void;
		attach: () => void;
		cleanup: () => void;
	}

	interface Window {
		SidebarTOC: {
			manager: ITOCManager | null;
		};
		FloatingTOC: {
			btn: HTMLElement | null;
			panel: HTMLElement | null;
			manager: ITOCManager | null;
			isPostPage: () => boolean;
		};
		toggleFloatingTOC: () => void;
		tocInternalNavigation: boolean;
		// swup is defined in global.d.ts
		// biome-ignore lint/suspicious/noExplicitAny: External library without types
		spine: any;
		closeAnnouncement: () => void;
		// __ROSETTAMusic type is defined in global.d.ts
		semifullScrollHandler?: (() => void) | undefined;
		initSemifullScrollDetection?: () => void;
	}
}

export {};
