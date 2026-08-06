<script lang="ts">
import I18nKey from "@i18n/i18nKey";
import { i18n } from "@i18n/translation";
import { onMount } from "svelte";
import Icon from "@/components/common/Icon.svelte";
import { DARK_MODE, LIGHT_MODE } from "@/constants/constants";
import type { LIGHT_DARK_MODE } from "@/types/config.ts";
import {
	applyThemeToDocument,
	getStoredTheme,
	setTheme,
} from "@/utils/setting-utils";

// Define Swup type for window object
interface SwupHooks {
	on(event: string, callback: () => void): void;
}

interface SwupInstance {
	hooks?: SwupHooks;
}

type WindowWithSwup = Window & { swup?: SwupInstance };

let mode: LIGHT_DARK_MODE = $state(LIGHT_MODE);

function nextMode(current: LIGHT_DARK_MODE): LIGHT_DARK_MODE {
	// 二态切换：只在亮色 ⇄ 暗色之间切换，移除了跟随系统按钮
	return current === LIGHT_MODE ? DARK_MODE : LIGHT_MODE;
}

function modeTitle(m: LIGHT_DARK_MODE): string {
	if (m === LIGHT_MODE) return `${i18n(I18nKey.lightMode)} · 点击切换到暗色`;
	return `${i18n(I18nKey.darkMode)} · 点击切换到亮色`;
}

function switchScheme(event?: MouseEvent) {
	mode = nextMode(mode);
	setTheme(mode, event);
}

// 使用onMount确保在组件挂载后正确初始化
onMount(() => {
	let storedTheme = getStoredTheme();
	// 二态迁移：如果旧用户 storage 里存的是 system，按当前系统主题解析成 light/dark 并存入，彻底不再出现 system
	if (storedTheme === ("system" as LIGHT_DARK_MODE)) {
		const resolved = window.matchMedia("(prefers-color-scheme: dark)").matches
			? DARK_MODE
			: LIGHT_MODE;
		try {
			localStorage.setItem("theme", resolved);
		} catch {
			/* ignore */
		}
		storedTheme = resolved;
	}
	mode = storedTheme;

	const currentTheme = document.documentElement.classList.contains("dark")
		? DARK_MODE
		: LIGHT_MODE;
	if (storedTheme !== currentTheme) {
		applyThemeToDocument(storedTheme);
	}

	// Swup 监听：切页后保持主题状态
	const handleContentReplace = () => {
		const newTheme = getStoredTheme();
		if (newTheme === ("system" as LIGHT_DARK_MODE)) {
			mode = window.matchMedia("(prefers-color-scheme: dark)").matches
				? DARK_MODE
				: LIGHT_MODE;
		} else {
			mode = newTheme;
		}
	};

	const win = window as WindowWithSwup;
	if (win.swup?.hooks) {
		win.swup.hooks.on("content:replace", handleContentReplace);
	} else {
		document.addEventListener("swup:enable", () => {
			const w = window as WindowWithSwup;
			if (w.swup?.hooks) {
				w.swup.hooks.on("content:replace", handleContentReplace);
			}
		});
	}

	// 监听主题变化事件
	const handleThemeChange = () => {
		let newTheme = getStoredTheme();
		if (newTheme === ("system" as LIGHT_DARK_MODE)) {
			newTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
				? DARK_MODE
				: LIGHT_MODE;
			try {
				localStorage.setItem("theme", newTheme);
			} catch {
				/* ignore */
			}
		}
		mode = newTheme;
	};

	window.addEventListener("theme-change", handleThemeChange);

	return () => {
		window.removeEventListener("theme-change", handleThemeChange);
	};
});
</script>

<div class="relative z-50">
    <button
		aria-label="切换主题（亮色 / 暗色）"
		aria-haspopup="false"
		class="relative btn-plain scale-animation rounded-lg h-9 w-9 md:h-11 md:w-11 active:scale-90"
		id="scheme-switch"
		title={modeTitle(mode)}
		on:click={(e) => switchScheme(e)}
	>
        <!-- 亮色：太阳 -->
        <div class="absolute inset-0 flex items-center justify-center transition-opacity duration-200" class:opacity-100={mode === LIGHT_MODE} class:opacity-0={mode !== LIGHT_MODE}>
            <Icon icon="material-symbols:wb-sunny-outline-rounded" class="text-[1.25rem]"></Icon>
        </div>
        <!-- 暗色：月亮 -->
        <div class="absolute inset-0 flex items-center justify-center transition-opacity duration-200" class:opacity-100={mode === DARK_MODE} class:opacity-0={mode !== DARK_MODE}>
            <Icon icon="material-symbols:dark-mode-outline-rounded" class="text-[1.25rem]"></Icon>
        </div>
    </button>
</div>