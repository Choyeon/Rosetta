import { url } from "@/utils/url-utils";

/**
 * 导航工具函数
 * 提供统一的页面导航功能，支持 Swup 无刷新跳转
 */

// ============ 路由边界：前台 ↔ 后台 / 登录 / OOBE / 错误页
// 命中时不交给 Swup，强制整页刷新，避免外壳布局残留。
// 按路径段 (segment) 判断，兼容站点部署在子路径 (base path) 的情况。
function shouldBypassSwup(targetHref: string | undefined): boolean {
	if (!targetHref) return false;
	if (
		targetHref.startsWith("http://") ||
		targetHref.startsWith("https://") ||
		targetHref.startsWith("//")
	) {
		return false;
	}
	if (targetHref.startsWith("#")) return false;
	try {
		const u = new URL(targetHref, "http://x");
		const p = u.pathname || "";
		const segments = p.split("/").filter((s) => s.length > 0);
		const first = segments[0] || "";
		const last = segments[segments.length - 1] || "";
		const hasAdmin = segments.some((s) => s === "admin");
		const hasLogin = segments.some((s) => s === "login");
		const hasOobe = segments.some((s) => s === "oobe");
		const isError =
			last === "404" ||
			last === "403" ||
			last === "500" ||
			first === "404" ||
			first === "403" ||
			first === "500";
		return hasAdmin || hasLogin || hasOobe || isError;
	} catch {
		return false;
	}
}

/**
 * 导航到指定页面
 * @param url 目标页面URL
 * @param options 导航选项
 */
export function navigateToPage(
	url: string,
	options?: {
		replace?: boolean;
		force?: boolean;
	},
): void {
	// 检查 URL 是否有效
	if (!url || typeof url !== "string") {
		console.warn("navigateToPage: Invalid URL provided");
		return;
	}

	// 如果是外部链接，直接跳转
	if (
		url.startsWith("http://") ||
		url.startsWith("https://") ||
		url.startsWith("//")
	) {
		window.open(url, "_blank");
		return;
	}

	// 如果是锚点链接，滚动到对应位置
	if (url.startsWith("#")) {
		const element = document.getElementById(url.slice(1));
		if (element) {
			element.scrollIntoView({ behavior: "smooth" });
		}
		return;
	}

	// 路由边界：跳转到后台 / 登录 / OOBE 等不同外壳的页面，必须整页刷新，不走 Swup
	if (shouldBypassSwup(url) || options?.force) {
		fallbackNavigation(url, options);
		return;
	}

	// 检查 Swup 是否可用
	if (typeof window !== "undefined" && window.swup) {
		try {
			// 使用 Swup 进行无刷新跳转
			if (options?.replace) {
				window.swup.navigate(url, { history: false });
			} else {
				window.swup.navigate(url);
			}
		} catch (error) {
			console.error("Swup navigation failed:", error);
			// 降级到普通跳转
			fallbackNavigation(url, options);
		}
	} else {
		// Swup 不可用时的降级处理
		fallbackNavigation(url, options);
	}
}

/**
 * 降级导航函数
 * 当 Swup 不可用时使用普通的页面跳转
 */
function fallbackNavigation(
	url: string,
	options?: {
		replace?: boolean;
		force?: boolean;
	},
): void {
	if (options?.replace) {
		window.location.replace(url);
	} else {
		window.location.href = url;
	}
}

/**
 * 检查 Swup 是否已准备就绪
 */
export function isSwupReady(): boolean {
	return typeof window !== "undefined" && !!window.swup;
}

/**
 * 等待 Swup 准备就绪
 * @param timeout 超时时间（毫秒）
 */
export function waitForSwup(timeout = 5000): Promise<boolean> {
	return new Promise((resolve) => {
		if (isSwupReady()) {
			resolve(true);
			return;
		}

		let timeoutId: NodeJS.Timeout;

		const checkSwup = () => {
			if (isSwupReady()) {
				clearTimeout(timeoutId);
				document.removeEventListener("swup:enable", checkSwup);
				resolve(true);
			}
		};

		// 监听 Swup 启用事件
		document.addEventListener("swup:enable", checkSwup);

		// 设置超时
		timeoutId = setTimeout(() => {
			document.removeEventListener("swup:enable", checkSwup);
			resolve(false);
		}, timeout);
	});
}

/**
 * 预加载页面
 * @param url 要预加载的页面URL
 */
export function preloadPage(url: string): void {
	if (!url || typeof url !== "string") {
		return;
	}

	// 如果 Swup 可用，使用其预加载功能
	if (isSwupReady() && window.swup.preload) {
		try {
			window.swup.preload(url);
		} catch (error) {
			console.warn("Failed to preload page:", error);
		}
	}
}

/**
 * 获取当前页面路径
 */
export function getCurrentPath(): string {
	return typeof window !== "undefined" ? window.location.pathname : "";
}

/**
 * 检查是否为首页
 */
export function isHomePage(): boolean {
	const path = getCurrentPath();
	return path === url("/") || path === url("");
}

/**
 * 检查是否为文章页面
 */
export function isPostPage(): boolean {
	const path = getCurrentPath();
	return path.startsWith(url("/posts/"));
}

/**
 * 检查两个路径是否相等
 */
export function pathsEqual(path1: string, path2: string): boolean {
	// 标准化路径（移除末尾斜杠）
	const normalize = (path: string) => {
		return path.endsWith("/") && path.length > 1 ? path.slice(0, -1) : path;
	};

	return normalize(path1) === normalize(path2);
}
