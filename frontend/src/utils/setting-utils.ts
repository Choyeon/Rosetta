import {
	BANNER_HEIGHT_EXTEND,
	DARK_MODE,
	DEFAULT_THEME,
	LIGHT_MODE,
	WALLPAPER_BANNER,
	WALLPAPER_FULLSCREEN,
	WALLPAPER_NONE,
	WALLPAPER_OVERLAY,
} from "@constants/constants";
import type { LIGHT_DARK_MODE, WALLPAPER_MODE } from "@/types/config";
import {
	backgroundWallpaper,
	displaySettingsConfig,
	expressiveCodeConfig,
	sakuraConfig,
	siteConfig,
} from "../config";
import { isHomePage as checkIsHomePage } from "./layout-utils";

// Declare global functions
declare global {
	interface Window {
		initSemifullScrollDetection?: () => void;
		semifullScrollHandler?: () => void;
	}
}

export function getDefaultHue(): number {
	const fallback = "250";
	// 检查是否在浏览器环境中
	if (typeof document === "undefined") {
		return Number.parseInt(fallback, 10);
	}
	const configCarrier = document.getElementById("config-carrier");
	return Number.parseInt(configCarrier?.dataset.hue || fallback, 10);
}

export function getDefaultTheme(): LIGHT_DARK_MODE {
	// 如果配置文件中设置了 defaultMode，使用配置的值
	// 否则使用 DEFAULT_THEME（向后兼容）
	const configured = siteConfig.themeColor.defaultMode ?? DEFAULT_THEME;
	// 二态迁移：如果配置写的是 "system"，按当前系统主题解析成 light/dark，再不返回 system
	if (configured === ("system" as LIGHT_DARK_MODE)) {
		return getSystemTheme();
	}
	return configured;
}

// 获取系统主题
export function getSystemTheme(): LIGHT_DARK_MODE {
	if (typeof window === "undefined") {
		return LIGHT_MODE;
	}
	return window.matchMedia("(prefers-color-scheme: dark)").matches
		? DARK_MODE
		: LIGHT_MODE;
}

// 解析主题（二态模式：已不存 system；保留对历史值的解析兼容）
export function resolveTheme(theme: LIGHT_DARK_MODE): LIGHT_DARK_MODE {
	if (theme === ("system" as LIGHT_DARK_MODE)) {
		return getSystemTheme();
	}
	return theme;
}

export function getHue(): number {
	// 先检查全局对象
	if (typeof window === "undefined" || !window.localStorage) {
		return getDefaultHue();
	}
	const stored = localStorage.getItem("hue");
	return stored ? Number.parseInt(stored, 10) : getDefaultHue();
}

export function setHue(hue: number): void {
	// 先检查是否在浏览器环境
	if (
		typeof window === "undefined" ||
		!window.localStorage ||
		typeof document === "undefined"
	) {
		return;
	}
	localStorage.setItem("hue", String(hue));
	const r = document.querySelector(":root") as HTMLElement;
	if (!r) {
		return;
	}
	r.style.setProperty("--hue", String(hue));
}

export function applyThemeToDocument(theme: LIGHT_DARK_MODE): void {
	// 检查是否在浏览器环境中
	if (typeof document === "undefined") {
		return;
	}

	// 二态迁移：如果 theme 是历史值 "system"，先解析成 light/dark（并写回 storage，不再反复进入 system 分支）
	let resolvedMode: LIGHT_DARK_MODE = theme;
	if (theme === ("system" as LIGHT_DARK_MODE)) {
		resolvedMode = getSystemTheme();
		try {
			localStorage.setItem("theme", resolvedMode);
		} catch {
			/* ignore */
		}
	}

	// 解析主题（二态：resolvedMode 一定是 light / dark）
	const resolvedTheme = resolvedMode;

	// 获取当前主题状态的完整信息
	const currentIsDark = document.documentElement.classList.contains("dark");
	const currentTheme = document.documentElement.getAttribute("data-theme");

	// 计算目标主题状态
	const targetIsDark = resolvedTheme === DARK_MODE;

	// 检测是否真的需要主题切换：
	// 1. dark类状态是否改变
	// 2. expressiveCode主题是否需要更新
	const needsThemeChange = currentIsDark !== targetIsDark;
	const expectedTheme = targetIsDark
		? expressiveCodeConfig.darkTheme
		: expressiveCodeConfig.lightTheme;
	const needsCodeThemeUpdate = currentTheme !== expectedTheme;

	// 如果既不需要主题切换也不需要代码主题更新，直接返回
	if (!needsThemeChange && !needsCodeThemeUpdate) {
		return;
	}

	// 批量 DOM 操作，减少重绘
	if (needsThemeChange) {
		if (targetIsDark) {
			document.documentElement.classList.add("dark");
		} else {
			document.documentElement.classList.remove("dark");
		}
	}

	// 同步 data-theme-mode 属性（二态：仅 light / dark）
	document.documentElement.dataset.themeMode = resolvedMode;

	// Set the theme for Expressive Code based on current mode
	if (needsCodeThemeUpdate) {
		document.documentElement.setAttribute("data-theme", expectedTheme);
	}
}

// 系统主题监听器引用
let systemThemeListener:
	| ((e: MediaQueryListEvent | MediaQueryList) => void)
	| null = null;

// 读取指定主题模式下的页面主背景色（"真实的"目标页面颜色，不是灰蒙板）
function readPageBgUnderTheme(targetResolvedDark: boolean): string {
	const root = document.documentElement;
	const styles = getComputedStyle(root);
	const readVar = (name: string): string =>
		styles.getPropertyValue(name).trim();

	// 优先：用 --page-bg（首页 variables.styl 的语义变量）
	const pbg = readVar("--page-bg");
	if (pbg) return pbg;

	// 其次：--b1（DaisyUI 语义基色）或 root 自身的 backgroundColor
	const b1 = readVar("--b1");
	if (b1) {
		// b1 是 "H S L" 三元组（不带 hsl()），需要包装
		const match = /^\s*([\d.]+)[,\s]+([\d.]+)%?[,\s]+([\d.]+)%?\s*$/.exec(b1);
		if (match) return `hsl(${match[1]} ${match[2]}% ${match[3]}%)`;
		if (/^hsl/i.test(b1) || /^#|^rgb|^oklch|^color\(/.test(b1)) return b1;
	}
	const bg = styles.backgroundColor;
	if (bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") return bg;
	return targetResolvedDark ? "#111114" : "#fafafa";
}

// 在"不产生肉眼闪烁"的前提下，临时切换到目标主题，同步读取 getComputedStyle 的颜色
function sneakPreview<T>(targetResolvedDark: boolean, runner: () => T): T {
	const root = document.documentElement;
	const hadDark = root.classList.contains("dark");
	const needFlip = hadDark !== targetResolvedDark;
	// 强制锁定渲染：把整页变成 visibility: hidden，然后同步 flush 后恢复
	// visibility 切换不会触发重绘，但浏览器 getComputedStyle 会正确读取
	const prevVisibility = root.style.visibility;
	root.style.visibility = "hidden";
	if (needFlip) {
		if (targetResolvedDark) root.classList.add("dark");
		else root.classList.remove("dark");
	}
	// 同步强制 reflow 以确保计算样式更新
	void root.offsetWidth;
	let result: T;
	try {
		result = runner();
	} finally {
		if (needFlip) {
			if (hadDark) root.classList.add("dark");
			else root.classList.remove("dark");
		}
		root.style.visibility = prevVisibility;
	}
	return result;
}

// 主题切换圆形 reveal：优先使用 View Transitions API（Element Plus 同款效果）
//   浏览器自动生成「旧主题截图」与「新主题截图」，我们只需决定对哪张截图做 clip-path circle() 动画：
//     · 亮 → 暗：裁剪 ::view-transition-new(root)（新暗色截图），circle(点击点 0) → circle(全屏 R) 外扩
//     · 暗 → 亮：裁剪 ::view-transition-old(root)（旧暗色截图），circle(全屏 R) → circle(点击点 0) 收缩
//   优势：截图由浏览器生成，永远与真实内容一致，不会"黑屏/内容消失"。
//   降级：不支持 startViewTransition 的浏览器（Firefox 等）仍走旧层的「克隆 body + 过渡」兜底。
export function playThemeReveal(
	x: number,
	y: number,
	targetResolvedDark: boolean,
	doSwitch: () => void,
): Promise<void> {
	if (typeof document === "undefined") {
		doSwitch();
		return Promise.resolve();
	}
	const root = document.documentElement;
	const currentlyDark = root.classList.contains("dark");
	const goingDark = targetResolvedDark && !currentlyDark;
	const goingLight = !targetResolvedDark && currentlyDark;

	// 同主题（几乎不会发生）：不做动画，避免抖动
	if (!goingDark && !goingLight) {
		try {
			doSwitch();
		} catch (e) {
			console.warn("[theme-reveal]", e);
		}
		return Promise.resolve();
	}

	const radius =
		Math.max(
			Math.hypot(x, y),
			Math.hypot(window.innerWidth - x, y),
			Math.hypot(x, window.innerHeight - y),
			Math.hypot(window.innerWidth - x, window.innerHeight - y),
		) * 1.15;

	// 支持 View Transitions API 的现代浏览器（Chromium / 新版 Safari 等）
	const supportsVT =
		typeof (document as any).startViewTransition === "function";
	if (supportsVT) {
		return new Promise<void>((resolve) => {
			// 标记方向，CSS 用来控制 ::view-transition-old/new 的 z-index
			root.setAttribute("data-vt-from", currentlyDark ? "dark" : "light");

			let settled = false;
			const finish = () => {
				if (settled) return;
				settled = true;
				root.removeAttribute("data-vt-from");
				resolve();
			};

			try {
				const vt: any = (document as any).startViewTransition(() => {
					try {
						doSwitch();
					} catch (e) {
						console.warn("[theme-reveal] doSwitch errored:", e);
					}
					return undefined;
				});

				vt.ready
					.then(() => {
						const expand = [
							`circle(0px at ${x}px ${y}px)`,
							`circle(${radius}px at ${x}px ${y}px)`,
						];
						const collapse = [
							`circle(${radius}px at ${x}px ${y}px)`,
							`circle(0px at ${x}px ${y}px)`,
						];

						let anim: any;
						if (goingDark) {
							// 亮→暗：新暗色截图（::view-transition-new）从点击点向外扩散露出
							anim = root.animate(
								{ clipPath: expand },
								{
									duration: 960,
									easing: "cubic-bezier(0.22, 1, 0.36, 1)",
									fill: "both",
									pseudoElement: "::view-transition-new(root)",
								},
							);
						} else {
							// 暗→亮：旧暗色截图（::view-transition-old）向点击点收缩消失，底下的亮色露出
							anim = root.animate(
								{ clipPath: collapse },
								{
									duration: 960,
									easing: "cubic-bezier(0.22, 1, 0.36, 1)",
									fill: "both",
									pseudoElement: "::view-transition-old(root)",
								},
							);
						}
						anim.finished.then(finish, finish);
					})
					.catch((err: any) => {
						console.warn("[theme-reveal] VT.ready errored:", err);
						finish();
					});

				// 双重兜底：若浏览器不真正触发 finished，超时后清理
				setTimeout(finish, 1500);
			} catch (err) {
				console.warn("[theme-reveal] VT fallback to instant switch:", err);
				try {
					doSwitch();
				} catch (_e) {
					/* noop */
				}
				finish();
			}
		});
	}

	// ──────────────────────────────────────────────────────────
	//  降级：不支持 View Transitions API → 克隆 body 快照过渡（保方向、保内容）
	// ──────────────────────────────────────────────────────────
	return new Promise<void>((resolve) => {
		const targetBg = sneakPreview(targetResolvedDark, () =>
			readPageBgUnderTheme(targetResolvedDark),
		);

		// ① 旧主题内容快照
		const oldLayer = document.createElement("div");
		oldLayer.setAttribute("aria-hidden", "true");
		oldLayer.style.cssText =
			"position:fixed;inset:0;z-index:2147483646;pointer-events:none;overflow:hidden;" +
			`background-color:${root.style.getPropertyValue("--page-bg") || (currentlyDark ? "#111114" : "#fafafa")};` +
			"transform:translateZ(0);";
		const oldBody = document.body.cloneNode(true) as HTMLElement;
		oldBody.setAttribute("data-theme-reveal-snapshot", "old");
		oldBody.style.cssText =
			"position:absolute;inset:0;margin:0;padding:0;width:100vw;height:100vh;overflow:hidden;pointer-events:none;transform:translateZ(0);";
		oldBody.querySelectorAll<HTMLElement>("*").forEach((el) => {
			try {
				el.style.transition = "none !important";
				el.style.animationPlayState = "paused";
				const tag = el.tagName;
				if (tag === "CANVAS" || tag === "VIDEO" || tag === "IFRAME")
					el.style.visibility = "hidden";
			} catch {
				/* noop */
			}
		});
		oldLayer.appendChild(oldBody);
		root.appendChild(oldLayer);

		// ② 真实切换 DOM 主题
		try {
			doSwitch();
		} catch (e) {
			console.warn("[theme-reveal] doSwitch errored:", e);
		}
		void root.offsetWidth;

		// ③ 新主题内容快照（对它做 clip-path reveal）
		const newLayer = document.createElement("div");
		newLayer.setAttribute("aria-hidden", "true");
		newLayer.style.cssText =
			"position:fixed;inset:0;z-index:2147483647;pointer-events:none;overflow:hidden;" +
			`background-color:${root.style.getPropertyValue("--page-bg") || targetBg};transform:translateZ(0);`;
		const newBody = document.body.cloneNode(true) as HTMLElement;
		newBody.setAttribute("data-theme-reveal-snapshot", "new");
		newBody.style.cssText =
			"position:absolute;inset:0;margin:0;padding:0;width:100vw;height:100vh;overflow:hidden;pointer-events:none;transform:translateZ(0);";
		newBody.querySelectorAll<HTMLElement>("*").forEach((el) => {
			try {
				el.style.transition = "none !important";
				el.style.animationPlayState = "paused";
				const tag = el.tagName;
				if (tag === "CANVAS" || tag === "VIDEO" || tag === "IFRAME")
					el.style.visibility = "hidden";
			} catch {
				/* noop */
			}
		});
		newLayer.appendChild(newBody);
		root.appendChild(newLayer);

		// ④ 初始 clip-path（无 transition，强制落地）
		if (goingDark) {
			newLayer.style.clipPath = `circle(0px at ${x}px ${y}px)`;
		} else {
			newLayer.style.clipPath = `circle(${radius}px at ${x}px ${y}px)`;
		}
		void newLayer.offsetWidth;

		// ⑤ 波纹（柔化圆圈硬边）
		const wave = document.createElement("div");
		wave.setAttribute("aria-hidden", "true");
		wave.style.cssText =
			"position:fixed;inset:0;z-index:2147483648;pointer-events:none;" +
			`background:radial-gradient(circle at ${x}px ${y}px, ` +
			`color-mix(in oklch, ${targetBg} 72%, transparent) 0%, ` +
			`color-mix(in oklch, ${targetBg} 50%, transparent) 42%, ` +
			`color-mix(in oklch, ${targetBg} 18%, transparent) 58%, transparent 72%, transparent 100%);` +
			"transform:translateZ(0);";
		root.appendChild(wave);
		if (goingDark) {
			wave.style.clipPath = `circle(0px at ${x}px ${y}px)`;
			wave.style.opacity = "0";
		} else {
			wave.style.clipPath = `circle(${radius}px at ${x}px ${y}px)`;
			wave.style.opacity = "0.85";
		}
		void wave.offsetWidth;

		// ⑥ 激活 transition + 双 rAF 写终点
		const layerTransition =
			"clip-path 960ms cubic-bezier(0.22, 1, 0.36, 1), opacity 820ms cubic-bezier(0.22, 1, 0.36, 1)";
		newLayer.style.transition = layerTransition;
		wave.style.transition = layerTransition;
		oldLayer.style.transition = "opacity 780ms cubic-bezier(0.22, 1, 0.36, 1)";

		requestAnimationFrame(() =>
			requestAnimationFrame(() => {
				if (goingDark) {
					newLayer.style.clipPath = `circle(${radius}px at ${x}px ${y}px)`;
					wave.style.clipPath = `circle(${radius}px at ${x}px ${y}px)`;
					wave.style.opacity = "0.9";
					setTimeout(() => {
						oldLayer.style.opacity = "0";
					}, 220);
				} else {
					newLayer.style.clipPath = `circle(0px at ${x}px ${y}px)`;
					wave.style.clipPath = `circle(0px at ${x}px ${y}px)`;
					wave.style.opacity = "0";
					setTimeout(() => {
						oldLayer.style.opacity = "0";
					}, 320);
				}
			}),
		);

		setTimeout(() => {
			try {
				if (oldLayer.parentNode) oldLayer.parentNode.removeChild(oldLayer);
			} catch {
				void 0;
			}
			try {
				if (newLayer.parentNode) newLayer.parentNode.removeChild(newLayer);
			} catch {
				void 0;
			}
			try {
				if (wave.parentNode) wave.parentNode.removeChild(wave);
			} catch {
				void 0;
			}
			resolve();
		}, 1060);
	});
}

// 跟踪前一次动画，避免快速点击竞态
let _revealRunning: Promise<void> | null = null;

export function setTheme(theme: LIGHT_DARK_MODE, event?: MouseEvent): void {
	// 检查是否在浏览器环境中
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}

	// 二态迁移：如果传入/历史值是 system，立即按当前系统主题解析成 light/dark，从此再不保留 system
	let finalMode: LIGHT_DARK_MODE = theme;
	if (finalMode === ("system" as LIGHT_DARK_MODE)) {
		finalMode = getSystemTheme();
	}

	// 保存到localStorage（只存 light / dark）
	localStorage.setItem("theme", finalMode);

	// 设置 data-theme-mode 属性，驱动图标切换（仅 light / dark）
	if (typeof document !== "undefined") {
		document.documentElement.dataset.themeMode = finalMode;
	}

	const targetIsDark = finalMode === DARK_MODE;

	// 若有位置信息（点击切换）使用圆形扩散/收缩动画
	const runApply = () => {
		applyThemeToDocument(finalMode);
		// 二态模式：不再存在"跟随系统"，所以不再需要系统主题监听器（直接清理即可）
		cleanupSystemThemeListener();
		if (typeof window !== "undefined") {
			window.dispatchEvent(new CustomEvent("theme-change"));
		}
	};

	if (
		event &&
		typeof event.clientX === "number" &&
		typeof event.clientY === "number"
	) {
		const prior = _revealRunning;
		const next = (async () => {
			if (prior) await prior.catch(() => {});
			await playThemeReveal(
				event.clientX,
				event.clientY,
				targetIsDark,
				runApply,
			);
		})();
		_revealRunning = next;
		void next.then(() => {
			if (_revealRunning === next) _revealRunning = null;
		});
	} else {
		runApply();
	}
}

// 设置系统主题监听器
export function setupSystemThemeListener(): void {
	// 先清理之前的监听器
	cleanupSystemThemeListener();

	if (typeof window === "undefined") {
		return;
	}

	const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

	// 处理系统主题变化的回调
	const handleSystemThemeChange = (e: MediaQueryListEvent | MediaQueryList) => {
		const isDark = e.matches;
		const currentIsDark = document.documentElement.classList.contains("dark");

		// 如果主题状态没有变化，直接返回
		if (currentIsDark === isDark) {
			return;
		}

		// 直接应用系统主题，不使用过渡保护类以避免大量重绘
		if (isDark) {
			document.documentElement.classList.add("dark");
		} else {
			document.documentElement.classList.remove("dark");
		}

		// Set the theme for Expressive Code
		const expressiveTheme = isDark
			? expressiveCodeConfig.darkTheme
			: expressiveCodeConfig.lightTheme;
		document.documentElement.setAttribute("data-theme", expressiveTheme);

		// 触发自定义事件通知其他组件（仅在真正切换时触发）
		window.dispatchEvent(new CustomEvent("theme-change"));
	};

	// 立即调用一次以设置初始状态
	handleSystemThemeChange(mediaQuery);

	// 监听系统主题变化（现代浏览器）
	if (mediaQuery.addEventListener) {
		mediaQuery.addEventListener("change", handleSystemThemeChange);
	} else {
		// 兼容旧浏览器
		mediaQuery.addListener(handleSystemThemeChange);
	}

	systemThemeListener = handleSystemThemeChange;
}

// 清理系统主题监听器
function cleanupSystemThemeListener() {
	if (typeof window === "undefined" || !systemThemeListener) {
		return;
	}

	const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

	if (mediaQuery.removeEventListener) {
		mediaQuery.removeEventListener("change", systemThemeListener);
	} else {
		// 兼容旧浏览器
		mediaQuery.removeListener(systemThemeListener);
	}

	systemThemeListener = null;
}

export function getStoredTheme(): LIGHT_DARK_MODE {
	// 检查是否在浏览器环境中
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultTheme();
	}
	const stored =
		(localStorage.getItem("theme") as LIGHT_DARK_MODE) || getDefaultTheme();
	// 二态迁移：如果历史 storage 存的是 system，立即解析成 light/dark 并写回，之后再不出现 system
	if (stored === ("system" as LIGHT_DARK_MODE)) {
		const resolved = getSystemTheme();
		try {
			localStorage.setItem("theme", resolved);
		} catch {
			/* ignore */
		}
		return resolved;
	}
	return stored;
}

// 初始化主题监听器（二态模式下不再有"跟随系统"，保留空壳避免调用点报错）
export function initThemeListener(): void {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return;
	}
	// 读取时会自动做二态迁移（system → light/dark），见 getStoredTheme
	void getStoredTheme();
}

// Wallpaper mode functions
export function applyWallpaperModeToDocument(
	mode: WALLPAPER_MODE,
	animate = true,
): void {
	// 获取当前的壁纸模式
	const currentMode =
		(document.documentElement.getAttribute(
			"data-wallpaper-mode",
		) as WALLPAPER_MODE) || backgroundWallpaper.mode;

	// 检查是否允许切换壁纸模式
	const isSwitchable = displaySettingsConfig.wallpaperModeSwitchable;
	if (!isSwitchable) {
		// 不允许切换时，仍需初始化当前模式的UI状态（添加 wallpaper-initialized 等）
		if (currentMode === mode) {
			adjustMainContentPosition(mode, false);
			ensureWallpaperState(mode);
		}
		return;
	}

	// 如果模式没有变化，直接返回
	if (currentMode === mode) {
		// 即使是相同模式，也要确保UI状态正确
		ensureWallpaperState(mode);
		return;
	}

	// 添加过渡保护类
	document.documentElement.classList.add("is-wallpaper-transitioning");

	// 更新数据属性
	document.documentElement.setAttribute("data-wallpaper-mode", mode);

	// 使用 requestAnimationFrame 确保在下一帧执行，避免闪屏
	requestAnimationFrame(() => {
		const body = document.body;

		// 移除所有壁纸相关的CSS类
		body.classList.remove(
			"enable-banner",
			"wallpaper-transparent",
			"no-banner-layout",
		);

		// 根据模式添加相应的CSS类
		switch (mode) {
			case WALLPAPER_BANNER:
				body.classList.add("enable-banner");
				showBannerMode(true);
				break;
			case WALLPAPER_FULLSCREEN:
				body.classList.add("no-banner-layout");
				showFullscreenMode(animate);
				break;
			case WALLPAPER_OVERLAY:
				body.classList.add("wallpaper-transparent");
				body.classList.add("no-banner-layout");
				showOverlayMode();
				break;
			case WALLPAPER_NONE:
				body.classList.add("no-banner-layout");
				hideAllWallpapers();
				break;
			default:
				body.classList.add("no-banner-layout");
				hideAllWallpapers();
				break;
		}

		// 更新导航栏透明模式
		updateNavbarTransparency(mode);

		// 在下一帧移除过渡保护类
		requestAnimationFrame(() => {
			document.documentElement.classList.remove("is-wallpaper-transitioning");
		});
	});
}

// 确保壁纸状态正确
function ensureWallpaperState(mode: WALLPAPER_MODE) {
	const body = document.body;

	// 移除所有壁纸相关的CSS类
	body.classList.remove(
		"enable-banner",
		"wallpaper-transparent",
		"no-banner-layout",
	);

	// 根据模式添加相应的CSS类
	switch (mode) {
		case WALLPAPER_BANNER:
			body.classList.add("enable-banner");
			showBannerMode();
			break;
		case WALLPAPER_FULLSCREEN:
			body.classList.add("no-banner-layout");
			showFullscreenMode();
			break;
		case WALLPAPER_OVERLAY:
			body.classList.add("wallpaper-transparent");
			body.classList.add("no-banner-layout");
			showOverlayMode();
			break;
		case WALLPAPER_NONE:
			body.classList.add("no-banner-layout");
			hideAllWallpapers();
			break;
	}

	// 更新导航栏透明模式
	updateNavbarTransparency(mode);
}

function showBannerMode(animate = false) {
	// 显示 wallpaper-wrapper 并切换为 banner 模式
	const wallpaperWrapper = document.getElementById("wallpaper-wrapper");
	if (wallpaperWrapper) {
		// 移除 overlay 和全屏壁纸模式类
		wallpaperWrapper.classList.remove("wallpaper-overlay");
		wallpaperWrapper.classList.remove("wallpaper-fullscreen");

		// 恢复 banner 模式的 top 定位
		wallpaperWrapper.style.top = `-${BANNER_HEIGHT_EXTEND}vh`;

		// 检查当前是否为首页
		const isHomePage = checkIsHomePage(window.location.pathname);
		const isMobile = window.innerWidth < 1024;

		// 移动端非首页时，不显示banner；桌面端始终显示
		if (isMobile && !isHomePage) {
			wallpaperWrapper.style.display = "none";
			wallpaperWrapper.classList.add("mobile-hide-banner");
		} else {
			// 首页或桌面端：先设置display，然后使用requestAnimationFrame确保渲染
			wallpaperWrapper.style.display = "block";
			wallpaperWrapper.style.setProperty("display", "block", "important");
			requestAnimationFrame(() => {
				wallpaperWrapper.classList.remove("hidden");
				wallpaperWrapper.classList.remove("opacity-0");
				wallpaperWrapper.classList.add("opacity-100");
				wallpaperWrapper.classList.remove("mobile-hide-banner");
			});
		}
	}

	// 显示横幅首页文本（如果启用且是首页）
	const bannerTextOverlay = document.querySelector(
		".banner-home-text-overlay",
	) as HTMLElement | null;
	if (bannerTextOverlay) {
		// 检查是否启用 homeText
		const homeTextEnabled = backgroundWallpaper.common?.homeText?.enable;

		// 检查当前是否为首页
		const isHomePage = checkIsHomePage(window.location.pathname);

		// 只有在启用且在首页时才显示
		if (homeTextEnabled && isHomePage) {
			bannerTextOverlay.classList.remove("hidden");
		} else {
			bannerTextOverlay.classList.add("hidden");
		}
		// 重置全屏模式的下移transform
		bannerTextOverlay.style.transition = "";
		bannerTextOverlay.style.transform = "";
	}

	// 调整主内容位置
	adjustMainContentPosition("banner", animate);

	// 处理移动端非首页主内容区域位置
	const mainContentWrapper = document.querySelector(
		".w-full.z-30.pointer-events-none",
	);
	if (mainContentWrapper) {
		const isHomePage = checkIsHomePage(window.location.pathname);
		const isMobile = window.innerWidth < 1024;
		// 只在移动端非首页时调整主内容位置
		if (isMobile && !isHomePage) {
			mainContentWrapper.classList.add("mobile-main-no-banner");
		} else {
			mainContentWrapper.classList.remove("mobile-main-no-banner");
		}
	}

	// 移除透明效果（横幅模式不使用半透明）
	adjustMainContentTransparency(false);

	// 调整导航栏透明度
	const navbar = document.getElementById("navbar");
	if (navbar) {
		// 获取导航栏透明模式配置（banner模式）
		const transparentMode =
			backgroundWallpaper.common?.navbar?.transparentMode || "semi";
		navbar.setAttribute("data-transparent-mode", transparentMode);

		// 重新初始化半透明模式滚动检测（如果需要）
		if (
			transparentMode === "semifull" &&
			typeof window.initSemifullScrollDetection === "function"
		) {
			window.initSemifullScrollDetection();
		}
	}
}

function showFullscreenMode(animate = false) {
	// 显示 wallpaper-wrapper 并切换为全屏壁纸模式
	const wallpaperWrapper = document.getElementById("wallpaper-wrapper");
	const isMobile = window.innerWidth < 1024;
	const isHomePage = checkIsHomePage(window.location.pathname);
	if (wallpaperWrapper) {
		// 移除 overlay 模式类
		wallpaperWrapper.classList.remove("wallpaper-overlay");
		// 添加全屏壁纸模式类
		wallpaperWrapper.classList.add("wallpaper-fullscreen");

		if (isMobile && !isHomePage) {
			// 移动端非首页时隐藏壁纸
			wallpaperWrapper.style.display = "none";
			wallpaperWrapper.classList.add("mobile-hide-banner");
		} else {
			// 显示壁纸
			wallpaperWrapper.style.display = "block";
			wallpaperWrapper.style.setProperty("display", "block", "important");
			wallpaperWrapper.style.top = "";
			requestAnimationFrame(() => {
				wallpaperWrapper.classList.remove("hidden");
				wallpaperWrapper.classList.remove("opacity-0");
				wallpaperWrapper.classList.add("opacity-100");
				wallpaperWrapper.classList.remove("mobile-hide-banner");
			});
		}
	}

	// 显示横幅首页文本（如果启用且是首页）
	const bannerTextOverlay = document.querySelector(
		".banner-home-text-overlay",
	) as HTMLElement | null;
	if (bannerTextOverlay) {
		const homeTextEnabled = backgroundWallpaper.common?.homeText?.enable;
		if (homeTextEnabled && isHomePage) {
			bannerTextOverlay.classList.remove("hidden");
			if (animate) {
				// 横幅文字跟随下移：wrapper已瞬间变为100vh，文字flex居中在50vh
				// 先用-17.5vh补偿到横幅位置(32.5vh)，再过渡到0(全屏居中50vh)
				bannerTextOverlay.style.transition = "none";
				bannerTextOverlay.style.transform = "translateY(-17.5vh)";
				requestAnimationFrame(() => {
					bannerTextOverlay.style.transition =
						"transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)";
					bannerTextOverlay.style.transform = "translateY(0)";
				});
			}
		} else {
			bannerTextOverlay.classList.add("hidden");
		}
	}

	// 调整主内容位置
	adjustMainContentPosition("fullscreen", animate);

	// 移除透明效果（全屏壁纸模式不使用半透明）
	adjustMainContentTransparency(false);

	// 调整导航栏透明度
	const navbar = document.getElementById("navbar");
	if (navbar) {
		const transparentMode =
			backgroundWallpaper.common?.navbar?.transparentMode || "semi";
		navbar.setAttribute("data-transparent-mode", transparentMode);

		if (
			transparentMode === "semifull" &&
			typeof window.initSemifullScrollDetection === "function"
		) {
			window.initSemifullScrollDetection();
		}
	}
}

function showOverlayMode() {
	// 切换 wallpaper-wrapper 为 overlay 模式
	const wallpaperWrapper = document.getElementById("wallpaper-wrapper");
	if (wallpaperWrapper) {
		// 添加 overlay 模式类，移除全屏壁纸模式类
		wallpaperWrapper.classList.remove("wallpaper-fullscreen");
		wallpaperWrapper.classList.add("wallpaper-overlay");
		// 显示壁纸
		wallpaperWrapper.style.display = "block";
		wallpaperWrapper.style.setProperty("display", "block", "important");
		wallpaperWrapper.style.top = "";
		requestAnimationFrame(() => {
			wallpaperWrapper.classList.remove("hidden");
			wallpaperWrapper.classList.remove("opacity-0");
			wallpaperWrapper.classList.add("opacity-100");
			wallpaperWrapper.classList.remove("mobile-hide-banner");
		});
	}

	// 隐藏横幅首页文本
	const bannerTextOverlay = document.querySelector(".banner-home-text-overlay");
	if (bannerTextOverlay) {
		bannerTextOverlay.classList.add("hidden");
	}

	// 调整主内容透明度
	adjustMainContentTransparency(true);

	// 调整布局为紧凑模式
	adjustMainContentPosition("overlay");
}

function hideAllWallpapers() {
	// 隐藏壁纸
	const wallpaperWrapper = document.getElementById("wallpaper-wrapper");

	if (wallpaperWrapper) {
		wallpaperWrapper.style.display = "none";
		wallpaperWrapper.classList.add("hidden");
		wallpaperWrapper.classList.add("opacity-0");
		wallpaperWrapper.classList.remove("wallpaper-overlay");
		wallpaperWrapper.classList.remove("wallpaper-fullscreen");
	}

	// 隐藏横幅首页文本
	const bannerTextOverlay = document.querySelector(".banner-home-text-overlay");
	if (bannerTextOverlay) {
		bannerTextOverlay.classList.add("hidden");
	}

	// 调整主内容位置和透明度
	adjustMainContentPosition("none");
	adjustMainContentTransparency(false);
}

function updateNavbarTransparency(mode: WALLPAPER_MODE) {
	const navbar = document.getElementById("navbar");
	if (!navbar) return;

	let transparentMode: string;
	let enableBlur: boolean;
	let blurAmount: number;

	// 根据当前壁纸模式设置导航栏透明模式和模糊效果
	if (mode === WALLPAPER_OVERLAY) {
		// 全屏透明模式
		transparentMode = "none";
		enableBlur = false;
		blurAmount = 0;
	} else if (mode === WALLPAPER_NONE) {
		// 纯色背景模式
		transparentMode = "none";
		enableBlur = false;
		blurAmount = 0;
	} else if (mode === WALLPAPER_FULLSCREEN) {
		// 全屏壁纸模式：使用 fullscreen 配置的透明模式和模糊效果
		transparentMode =
			backgroundWallpaper.common?.navbar?.transparentMode || "semi";
		enableBlur = backgroundWallpaper.common?.navbar?.enableBlur ?? true;
		blurAmount = backgroundWallpaper.common?.navbar?.blur ?? 20;
	} else {
		// Banner模式：使用配置的透明模式和模糊效果
		transparentMode =
			backgroundWallpaper.common?.navbar?.transparentMode || "semi";
		enableBlur = backgroundWallpaper.common?.navbar?.enableBlur ?? true;
		blurAmount = backgroundWallpaper.common?.navbar?.blur ?? 20;
	}

	// 更新导航栏的透明模式属性
	navbar.setAttribute("data-transparent-mode", transparentMode);
	navbar.setAttribute("data-enable-blur", String(enableBlur));
	navbar.style.setProperty("--navbar-glass-blur", `${blurAmount}px`);

	// 移除现有的透明模式类
	navbar.classList.remove(
		"navbar-transparent-semi",
		"navbar-transparent-full",
		"navbar-transparent-semifull",
	);

	// 移除scrolled类
	navbar.classList.remove("scrolled");

	// 滚动检测功能
	if (
		transparentMode === "semifull" &&
		(mode === WALLPAPER_BANNER || mode === WALLPAPER_FULLSCREEN) &&
		typeof window.initSemifullScrollDetection === "function"
	) {
		// 在Banner和全屏壁纸模式的semifull下启用滚动检测
		window.initSemifullScrollDetection();
	} else if (window.semifullScrollHandler) {
		// 移除滚动监听器
		window.removeEventListener("scroll", window.semifullScrollHandler);
		delete window.semifullScrollHandler;
	}
}

// 跟踪全屏模式动画的 setTimeout，快速切换时需要取消
let fullscreenAnimationTimeout: ReturnType<typeof setTimeout> | null = null;

function adjustMainContentPosition(
	mode: WALLPAPER_MODE | "banner" | "none" | "overlay" | "fullscreen",
	animate = false,
) {
	const mainContent = document.querySelector(
		".w-full.z-30.pointer-events-none",
	) as HTMLElement;
	if (!mainContent) return;

	// 取消上一次全屏模式动画的 setTimeout，防止快速切换时竞态覆盖
	if (fullscreenAnimationTimeout) {
		clearTimeout(fullscreenAnimationTimeout);
		fullscreenAnimationTimeout = null;
	}

	// 移除现有的位置类
	mainContent.classList.remove("mobile-main-no-banner", "no-banner-layout");

	switch (mode) {
		case "banner": {
			// Banner模式：主内容在banner下方
			const isHome = checkIsHomePage(window.location.pathname);
			const bannerTargetTop = "calc(var(--banner-height) - 3.5rem)";

			// 禁用 CSS transition，防止整个定位过程中的值变化触发过渡动画
			mainContent.style.setProperty("transition", "none", "important");
			// 清除 fullscreen 模式特有的 inline 样式（position: relative, top: 0 等）
			mainContent.style.position = "";
			mainContent.style.zIndex = "";
			mainContent.style.top = "";
			mainContent.style.setProperty("margin-top", "");

			if (!isHome) {
				mainContent.classList.add("mobile-main-no-banner");
				if (window.innerWidth < 1024) {
					mainContent.style.setProperty("top", "5.5rem", "important");
				} else {
					mainContent.style.setProperty("top", bannerTargetTop, "important");
				}
			} else {
				mainContent.style.setProperty("top", bannerTargetTop, "important");
			}
			const bannerGrid = document.getElementById("main-grid");
			if (bannerGrid) {
				bannerGrid.style.transform = "";
				bannerGrid.style.transition = "";
			}
			// 所有定位操作完成后，强制回流并恢复 CSS transition
			void mainContent.offsetWidth;
			mainContent.style.removeProperty("transition");
			break;
		}
		case "fullscreen": {
			// 全屏壁纸模式：壁纸已在文档流中占100vh，主内容紧跟其后
			const isFullscreenMobile = window.innerWidth < 1024;
			const isFullscreenHome = checkIsHomePage(window.location.pathname);
			if (isFullscreenMobile && !isFullscreenHome) {
				// 移动端非首页：壁纸已隐藏，主内容从导航栏下方开始
				mainContent.classList.add("mobile-main-no-banner");
				mainContent.classList.add("no-banner-layout");
				mainContent.style.setProperty("top", "5.5rem", "important");
				mainContent.style.setProperty("margin-top", "0", "important");
				mainContent.style.position = "";
				mainContent.style.minHeight = "";
				mainContent.style.transition = "";
				break;
			}

			if (animate) {
				// 运行时切换：从当前位置动画滑到壁纸下方，完成后切换为 relative
				const computedTop = mainContent.getBoundingClientRect().top;
				mainContent.style.transition = "none";
				mainContent.style.position = "absolute";
				mainContent.style.zIndex = "30";
				mainContent.style.setProperty("top", `${computedTop}px`, "important");
				// absolute 定位下 margin-top 不影响布局，提前设好最终值避免切换 relative 时跳变
				mainContent.style.setProperty("margin-top", "1rem", "important");
				mainContent.classList.add("no-banner-layout");
				void mainContent.offsetWidth;
				mainContent.style.setProperty(
					"transition",
					"top 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)",
					"important",
				);
				mainContent.style.setProperty("top", "100vh", "important");
				fullscreenAnimationTimeout = setTimeout(() => {
					mainContent.style.transition = "none";
					mainContent.style.position = "relative";
					mainContent.style.setProperty("top", "0", "important");
					void mainContent.offsetWidth;
					mainContent.style.transition = "";
				}, 450);
			} else {
				// 初始化：直接设置位置，无需动画
				mainContent.classList.add("no-banner-layout");
				mainContent.style.position = "relative";
				mainContent.style.zIndex = "30";
				mainContent.style.setProperty("top", "0", "important");
				mainContent.style.setProperty("margin-top", "1rem", "important");
				mainContent.style.transition = "";
			}
			break;
		}
		case "overlay":
			// Overlay模式：使用紧凑布局，主内容从导航栏下方开始
			mainContent.classList.add("no-banner-layout");
			mainContent.style.setProperty("top", "5.5rem", "important");
			mainContent.style.setProperty("margin-top", "0", "important");
			mainContent.style.position = "";
			mainContent.style.minHeight = "";
			mainContent.style.transition = "";
			break;
		case "none":
			// 无壁纸模式：主内容从导航栏下方开始
			mainContent.classList.add("no-banner-layout");
			mainContent.style.setProperty("top", "5.5rem", "important");
			mainContent.style.setProperty("margin-top", "0", "important");
			mainContent.style.position = "";
			mainContent.style.minHeight = "";
			mainContent.style.transition = "";
			break;
		default:
			mainContent.style.setProperty("top", "5.5rem", "important");
			mainContent.style.position = "";
			mainContent.style.minHeight = "";
			mainContent.style.transition = "";
			break;
	}

	// 定位完成后显示主内容，防止初始加载时壁纸初始化前的内容闪烁
	mainContent.style.visibility = "visible";
	document.body.classList.add("wallpaper-initialized");
}

function adjustMainContentTransparency(enable: boolean) {
	const mainContent = document.querySelector(
		".w-full.z-30.pointer-events-none",
	);
	const body = document.body;

	if (enable) {
		if (mainContent) {
			mainContent.classList.add("wallpaper-transparent");
		}
		if (body) {
			body.classList.add("wallpaper-transparent");
		}
	} else {
		if (mainContent) {
			mainContent.classList.remove("wallpaper-transparent");
		}
		if (body) {
			body.classList.remove("wallpaper-transparent");
		}
	}
}

export function setWallpaperMode(mode: WALLPAPER_MODE): void {
	// 检查是否在浏览器环境中
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}
	localStorage.setItem("wallpaperMode", mode);
	applyWallpaperModeToDocument(mode);
	if (typeof window !== "undefined") {
		window.dispatchEvent(
			new CustomEvent("wallpaperModeChange", {
				detail: { mode },
			}),
		);
	}
}

export function initWallpaperMode(): void {
	// 初始化透明模式参数（透明度/模糊度/卡片透明度）
	applyStoredOverlaySettingsToDocument();
	const storedMode = getStoredWallpaperMode();
	applyWallpaperModeToDocument(storedMode, false);
}

export function getStoredWallpaperMode(): WALLPAPER_MODE {
	// 检查是否在浏览器环境中
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return backgroundWallpaper.mode;
	}

	const isSwitchable = displaySettingsConfig.wallpaperModeSwitchable;
	if (!isSwitchable) {
		localStorage.removeItem("wallpaperMode");
		return backgroundWallpaper.mode;
	}

	return (
		(localStorage.getItem("wallpaperMode") as WALLPAPER_MODE) ||
		backgroundWallpaper.mode
	);
}

// Overlay settings functions
function clampNumber(value: number, min: number, max: number): number {
	return Math.min(max, Math.max(min, value));
}

export function getDefaultOverlayOpacity(): number {
	return backgroundWallpaper.overlay?.opacity ?? 0.8;
}

export function getDefaultOverlayBlur(): number {
	return backgroundWallpaper.overlay?.blur ?? 0;
}

export function getDefaultOverlayCardOpacity(): number {
	return backgroundWallpaper.overlay?.cardOpacity ?? 0.6;
}

export function getStoredOverlayOpacity(): number {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultOverlayOpacity();
	}
	const stored = localStorage.getItem("overlayOpacity");
	if (stored === null) {
		return getDefaultOverlayOpacity();
	}
	const parsed = Number.parseFloat(stored);
	if (Number.isNaN(parsed)) {
		return getDefaultOverlayOpacity();
	}
	return clampNumber(parsed, 0, 1);
}

export function getStoredOverlayBlur(): number {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultOverlayBlur();
	}
	const stored = localStorage.getItem("overlayBlur");
	if (stored === null) {
		return getDefaultOverlayBlur();
	}
	const parsed = Number.parseFloat(stored);
	if (Number.isNaN(parsed)) {
		return getDefaultOverlayBlur();
	}
	return clampNumber(parsed, 0, 20);
}

export function getStoredOverlayCardOpacity(): number {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultOverlayCardOpacity();
	}
	const stored = localStorage.getItem("overlayCardOpacity");
	if (stored === null) {
		return getDefaultOverlayCardOpacity();
	}
	const parsed = Number.parseFloat(stored);
	if (Number.isNaN(parsed)) {
		return getDefaultOverlayCardOpacity();
	}
	return clampNumber(parsed, 0, 1);
}

export function applyOverlayOpacityToDocument(opacity: number): void {
	if (typeof document === "undefined") {
		return;
	}
	const safeOpacity = clampNumber(opacity, 0, 1);
	const wallpaperWrapper = document.getElementById("wallpaper-wrapper");
	if (wallpaperWrapper) {
		wallpaperWrapper.style.setProperty(
			"--overlay-opacity",
			String(safeOpacity),
		);
	}
}

export function applyOverlayBlurToDocument(blur: number): void {
	if (typeof document === "undefined") {
		return;
	}
	const safeBlur = clampNumber(blur, 0, 20);
	const wallpaperWrapper = document.getElementById("wallpaper-wrapper");
	if (wallpaperWrapper) {
		wallpaperWrapper.style.setProperty("--overlay-blur", `${safeBlur}px`);
	}
}

export function applyOverlayCardOpacityToDocument(cardOpacity: number): void {
	if (typeof document === "undefined") {
		return;
	}
	const safeCardOpacity = clampNumber(cardOpacity, 0, 1);
	document.documentElement.style.setProperty(
		"--card-transparent-opacity",
		String(safeCardOpacity),
	);
}

export function setOverlayOpacity(opacity: number): void {
	const safeOpacity = clampNumber(opacity, 0, 1);
	if (
		typeof localStorage !== "undefined" &&
		typeof localStorage.setItem === "function"
	) {
		localStorage.setItem("overlayOpacity", String(safeOpacity));
	}
	applyOverlayOpacityToDocument(safeOpacity);
}

export function setOverlayBlur(blur: number): void {
	const safeBlur = clampNumber(blur, 0, 20);
	if (
		typeof localStorage !== "undefined" &&
		typeof localStorage.setItem === "function"
	) {
		localStorage.setItem("overlayBlur", String(safeBlur));
	}
	applyOverlayBlurToDocument(safeBlur);
}

export function setOverlayCardOpacity(cardOpacity: number): void {
	const safeCardOpacity = clampNumber(cardOpacity, 0, 1);
	if (
		typeof localStorage !== "undefined" &&
		typeof localStorage.setItem === "function"
	) {
		localStorage.setItem("overlayCardOpacity", String(safeCardOpacity));
	}
	applyOverlayCardOpacityToDocument(safeCardOpacity);
}

export function applyStoredOverlaySettingsToDocument(): void {
	applyOverlayOpacityToDocument(getStoredOverlayOpacity());
	applyOverlayBlurToDocument(getStoredOverlayBlur());
	applyOverlayCardOpacityToDocument(getStoredOverlayCardOpacity());
}

// Waves animation functions
export function getDefaultWavesEnabled(): boolean {
	const wavesConfig = backgroundWallpaper.common?.waves?.enable;
	if (typeof wavesConfig === "object") {
		// 如果是分设备配置，检查当前设备
		const isMobile =
			typeof window !== "undefined" ? window.innerWidth < 768 : false;
		return isMobile
			? (wavesConfig.mobile ?? false)
			: (wavesConfig.desktop ?? false);
	}
	return wavesConfig ?? false;
}

export function getStoredWavesEnabled(): boolean {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultWavesEnabled();
	}
	const stored = localStorage.getItem("wavesEnabled");
	if (stored === null) {
		return getDefaultWavesEnabled();
	}
	return stored === "true";
}

export function setWavesEnabled(enabled: boolean): void {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}
	localStorage.setItem("wavesEnabled", String(enabled));
	applyWavesEnabledToDocument(enabled);
}

export function applyWavesEnabledToDocument(enabled: boolean): void {
	if (typeof document === "undefined") {
		return;
	}
	// 更新 html 属性，CSS 会立即生效
	document.documentElement.setAttribute("data-waves-enabled", String(enabled));
	// 同时更新元素样式（兼容性）
	const wavesElement = document.getElementById("header-waves");
	if (wavesElement) {
		if (enabled) {
			wavesElement.style.display = "";
			wavesElement.classList.remove("waves-disabled");
		} else {
			wavesElement.style.display = "none";
			wavesElement.classList.add("waves-disabled");
		}
	}
}

// Gradient transition functions
export function getDefaultGradientEnabled(): boolean {
	const gradientConfig = backgroundWallpaper.common?.gradient?.enable;
	if (typeof gradientConfig === "object") {
		const isMobile =
			typeof window !== "undefined" ? window.innerWidth < 768 : false;
		return isMobile
			? (gradientConfig.mobile ?? true)
			: (gradientConfig.desktop ?? true);
	}
	return gradientConfig ?? true;
}

export function getStoredGradientEnabled(): boolean {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultGradientEnabled();
	}
	const stored = localStorage.getItem("gradientEnabled");
	if (stored === null) {
		return getDefaultGradientEnabled();
	}
	return stored === "true";
}

export function setGradientEnabled(enabled: boolean): void {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}
	localStorage.setItem("gradientEnabled", String(enabled));
	applyGradientEnabledToDocument(enabled);
}

export function applyGradientEnabledToDocument(enabled: boolean): void {
	if (typeof document === "undefined") {
		return;
	}
	document.documentElement.setAttribute(
		"data-gradient-enabled",
		String(enabled),
	);
	const gradientElement = document.getElementById("wallpaper-gradient");
	if (gradientElement) {
		if (enabled) {
			gradientElement.style.display = "";
			gradientElement.classList.remove("gradient-disabled");
		} else {
			gradientElement.style.display = "none";
			gradientElement.classList.add("gradient-disabled");
		}
	}
}

// Sakura effect functions
export function getDefaultSakuraEnabled(): boolean {
	return sakuraConfig?.enable ?? false;
}

export function getStoredSakuraEnabled(): boolean {
	if (typeof localStorage === "undefined") {
		return getDefaultSakuraEnabled();
	}
	const stored = localStorage.getItem("sakuraEnabled");
	if (stored === null) {
		return getDefaultSakuraEnabled();
	}
	return stored === "true";
}

export function setSakuraEnabled(enabled: boolean): void {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}
	localStorage.setItem("sakuraEnabled", String(enabled));
	document.documentElement.setAttribute("data-sakura-enabled", String(enabled));
	// 实时切换樱花特效
	window.dispatchEvent(
		new CustomEvent("sakuraToggle", { detail: { enabled } }),
	);
}

// Banner title functions
export function getDefaultBannerTitleEnabled(): boolean {
	return backgroundWallpaper.common?.homeText?.enable ?? true;
}

export function getDefaultBannerCarouselEnabled(): boolean {
	return backgroundWallpaper.common?.carousel?.enable ?? false;
}

export function getStoredBannerTitleEnabled(): boolean {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultBannerTitleEnabled();
	}
	const stored = localStorage.getItem("bannerTitleEnabled");
	if (stored === null) {
		return getDefaultBannerTitleEnabled();
	}
	return stored === "true";
}

export function getStoredBannerCarouselEnabled(): boolean {
	const isSwitchable = displaySettingsConfig.bannerCarouselSwitchable;
	if (!isSwitchable) {
		return getDefaultBannerCarouselEnabled();
	}
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.getItem !== "function"
	) {
		return getDefaultBannerCarouselEnabled();
	}
	const stored = localStorage.getItem("bannerCarouselEnabled");
	if (stored === null) {
		return getDefaultBannerCarouselEnabled();
	}
	return stored === "true";
}

export function setBannerTitleEnabled(enabled: boolean): void {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}
	localStorage.setItem("bannerTitleEnabled", String(enabled));
	applyBannerTitleEnabledToDocument(enabled);
}

export function setBannerCarouselEnabled(enabled: boolean): void {
	const safeEnabled = !!enabled;
	const isSwitchable = displaySettingsConfig.bannerCarouselSwitchable;
	if (
		isSwitchable &&
		typeof localStorage !== "undefined" &&
		typeof localStorage.setItem === "function"
	) {
		localStorage.setItem("bannerCarouselEnabled", String(safeEnabled));
	}
	applyBannerCarouselEnabledToDocument(safeEnabled);
	if (typeof window !== "undefined") {
		window.dispatchEvent(
			new CustomEvent("bannerCarouselChange", {
				detail: { enabled: safeEnabled },
			}),
		);
	}
}

export function applyBannerTitleEnabledToDocument(enabled: boolean): void {
	if (typeof document === "undefined") {
		return;
	}
	// 更新 html 属性，CSS 会立即生效
	document.documentElement.setAttribute(
		"data-banner-title-enabled",
		String(enabled),
	);
	// 同时更新元素样式（兼容性）
	const bannerTextOverlay = document.querySelector(
		".banner-home-text-overlay",
	) as HTMLElement;
	if (bannerTextOverlay) {
		if (enabled) {
			bannerTextOverlay.classList.remove("user-hidden");
		} else {
			bannerTextOverlay.classList.add("user-hidden");
		}
	}
}

export function applyBannerCarouselEnabledToDocument(enabled: boolean): void {
	if (typeof document === "undefined") {
		return;
	}
	document.documentElement.setAttribute(
		"data-banner-carousel-enabled",
		String(enabled),
	);
}

// Card border functions
export function getDefaultCardBorderEnabled(): boolean {
	return siteConfig.card?.border ?? false;
}

export function getStoredCardBorderEnabled(): boolean {
	if (typeof localStorage === "undefined") {
		return getDefaultCardBorderEnabled();
	}
	const stored = localStorage.getItem("cardBorderEnabled");
	if (stored === null) {
		return getDefaultCardBorderEnabled();
	}
	return stored === "true";
}

export function setCardBorderEnabled(enabled: boolean): void {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}
	localStorage.setItem("cardBorderEnabled", String(enabled));
	if (enabled) {
		document.documentElement.classList.add("enable-card-border");
	} else {
		document.documentElement.classList.remove("enable-card-border");
	}
}

// Card follow theme functions
export function getDefaultCardFollowThemeEnabled(): boolean {
	return siteConfig.card?.followTheme ?? false;
}

export function getStoredCardFollowThemeEnabled(): boolean {
	if (typeof localStorage === "undefined") {
		return getDefaultCardFollowThemeEnabled();
	}
	const stored = localStorage.getItem("cardFollowThemeEnabled");
	if (stored === null) {
		return getDefaultCardFollowThemeEnabled();
	}
	return stored === "true";
}

export function setCardFollowThemeEnabled(enabled: boolean): void {
	if (
		typeof localStorage === "undefined" ||
		typeof localStorage.setItem !== "function"
	) {
		return;
	}
	localStorage.setItem("cardFollowThemeEnabled", String(enabled));
	if (enabled) {
		document.body.classList.add("card-follow-theme-hue");
	} else {
		document.body.classList.remove("card-follow-theme-hue");
	}
}
