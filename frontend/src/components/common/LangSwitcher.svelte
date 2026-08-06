<script lang="ts">
import { createEventDispatcher, onMount } from "svelte";
import {
	currentLang,
	type Lang,
	SUPPORTED_LANGS,
	setLang,
} from "../../i18n/translation";

let isOpen = false;
const dispatch = createEventDispatcher();

// 使用 lipis/flag-icons 开源项目的高质量标准国旗 SVG（4:3 官方比例）
// 参考：https://github.com/lipis/flag-icons  (MIT License)
const FLAG_SVG: Record<Lang, string> = {
	// 中国国旗 🇨🇳（标准版：鲜红底 + 精确几何位置的五颗黄星）
	zh_CN: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480" width="22" height="16.5" style="border-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)">
<path fill="#ee1c25" d="M0 0h640v480H0z"/>
<path fill="#ffde00" d="M120.4 121.6 140.4 79l20 42.6 42.6.1-34.7 25.3 13.3 42.6-34.8-25.3-34.7 25.3 13.2-42.6-34.7-25.3 42.6-.1z"/>
<path fill="#ffde00" d="m240 48.1 3.7 11.5 12.1.5-9.8 7 3.8 11.4-9.8-6.9-9.8 7 3.8-11.4-9.8-7 12.1-.5zm48 47.7 3.7 11.5 12.1.5-9.8 6.9 3.8 11.5-9.8-7-9.8 6.9 3.8-11.5-9.8-7 12.1-.4zm0 72.2 3.7 11.5 12.1.5-9.8 7 3.8 11.4-9.8-6.9-9.8 7 3.8-11.4-9.8-7 12.1-.5zm-48 47.7 3.7 11.5 12.1.5-9.8 6.9 3.8 11.5-9.8-7-9.8 6.9 3.8-11.5-9.8-7 12.1-.4z"/>
</svg>`,
	// 台湾地区旗帜（繁体中文） - 青天白日满地红
	zh_TW: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480" width="22" height="16.5" style="border-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)">
<path fill="#fe0000" d="M0 0h640v480H0z"/>
<path fill="#000095" d="M0 0h360v240H0z"/>
<circle cx="180" cy="120" r="70" fill="#fff"/>
<circle cx="180" cy="120" r="60" fill="#000095"/>
<g fill="#fff">
<path d="M180 45v18h15L180 52l15-18h-15v-18h-6v18h-15l15 11-15 7h15v18z"/>
<path d="M80 93l16 9h-12l-8-16zm10 30 19-1-9 16zm18-107 19 1-14 12zm20 6 13 14 16-4-10 14zm261 1 11-15-15 10zm-10 107-3-17 17 4zm-271 77 17-5-4 16zm268 19-17-4 10 16z"/>
</g>
</svg>`,
	// 美国国旗 🇺🇸（标准版：红白间条 + 蓝色星区）
	en: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480" width="22" height="16.5" style="border-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)">
<path fill="#bd3d44" d="M0 0h640v480H0"/>
<path stroke="#fff" stroke-width="36.9" d="M0 55.4h640M0 129h640M0 203h640M0 277h640M0 351h640M0 425h640"/>
<path fill="#192f5d" d="M0 0h364.8v258.5H0"/>
<g fill="#fff">
<path d="M0 28.7 31.1 55h27l-31.1-27zM62.2 0l31 26.3h27L89.2 0zM124.3 28.7 155.4 55h27l-31.1-27zM186.5 0l31 26.3h27L213.4 0zM248.6 28.7 279.7 55h27L275.6 28.7zM310.7 0l31.1 26.3H369l-31-26.3zM0 83.7 31.1 110h27L0 83.7zM62.2 55l31 26.3h27L89.2 55zm62.1 28.7L155.4 110h27L115.3 83.7zm62.2-28.7 31 26.3h27L175.4 55zm62.1 28.7L279.7 110h27l-44.1-26.3zm62.2-28.7 31.1 26.3H369l-31-26.3zM0 138.7 31.1 165h27L0 138.7zm62.2-28.7L93.2 135h27l-31-25zm62.1 28.6L155.4 165h27l-40.1-26.4zm62.2-28.6 31 26.4h27L175.4 110zm62.1 28.6L279.7 165h27l-44.1-26.4zm62.2-28.6 31.1 26.4H369l-31-26.4zM0 193.7 31.1 220h27L0 193.7zm62.2-28.7L93.2 190h27l-31-25zm62.1 28.6L155.4 220h27l-40.1-26.4zm62.2-28.6 31 26.4h27L175.4 165zm62.1 28.6L279.7 220h27l-44.1-26.4zm62.2-28.6 31.1 26.4H369l-31-26.4zM0 248.7 31.1 275h27L0 248.7zm62.2-28.7L93.2 245h27l-31-25zm62.1 28.6L155.4 275h27l-40.1-26.4zm62.2-28.6 31 26.4h27L175.4 220zm62.1 28.6L279.7 275h27l-44.1-26.4zm62.2-28.6 31.1 26.4H369l-31-26.4z"/>
</g>
</svg>`,
	// 日本国旗 🇯🇵（标准版：白底红日）
	ja: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480" width="22" height="16.5" style="border-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)">
<defs><clipPath id="jp"><path fill-opacity=".7" d="M-88 32h640v480H-88z"/></clipPath></defs>
<g fill-rule="evenodd" stroke-width="1pt" clip-path="url(#jp)" transform="translate(88 -32)">
<path fill="#fff" d="M-128 32h720v480h-720z"/>
<circle cx="232" cy="272" r="149.3" fill="#bc002d"/>
</g>
</svg>`,
};

$: currentFlagSvg = FLAG_SVG[$currentLang as Lang] || FLAG_SVG.zh_CN;

function toggle(e: MouseEvent) {
	e.stopPropagation();
	isOpen = !isOpen;
}

function stopPropagation(e: Event) {
	e.stopPropagation();
}

function selectLang(lang: Lang) {
	setLang(lang);
	isOpen = false;
	dispatch("change", lang);
	// 语言切换后必须强制整页重载：导航、页脚、侧边栏、文章正文等所有 SSR 渲染的
	// i18n 文本只在请求时确定，不 reload 无法完全刷新成目标语言。
	//
	// 关键实现选择：
	//   不使用 window.location.replace(href) / window.location.reload() —— 两者在现代
	//   Chrome 中都可能被判定为 no-op（跳转同 URL），或者因调用上下文而被忽略。
	//   最稳妥的做法是：在当前 URL 上附加一个时间戳 query 参数，然后通过
	//   window.location.href = newHref 主动触发导航，这 100% 会触发一次新导航。
	//
	// requestAnimationFrame + setTimeout 0 保证当前事件循环（Svelte 更新、
	// dispatch、cookie 写入、DOM 属性设置）全部 flush 之后再执行跳转。
	requestAnimationFrame(() => {
		window.setTimeout(() => {
			try {
				const here = new URL(window.location.href);
				const qp = `_lang_reload=${encodeURIComponent(lang)}_${Date.now().toString(36)}`;
				here.searchParams.set("_lang_reload", qp);
				// 跳转到带新参数的 URL，浏览器会完全重新请求文档。
				// 使用 replace 避免在 history 里留下重复项，不影响回退体验。
				window.location.replace(here.toString());
			} catch (_e) {
				// 兜底：直接赋值，保证一定跳
				const sep = window.location.href.includes("?") ? "&" : "?";
				const nonce = `_lang_reload=${Date.now().toString(36)}`;
				window.location.href = `${window.location.href}${sep}${nonce}`;
			}
		}, 30);
	});
}

onMount(() => {
	const handleClick = (e: Event) => {
		// 只在点击目标不位于 .lang-switcher 内部时关闭菜单（避免点自己或子项关自己）
		const target = e.target as Node;
		const switcher = document.querySelector<HTMLElement>(".lang-switcher");
		if (switcher && target && switcher.contains(target)) {
			return;
		}
		if (isOpen) isOpen = false;
	};
	document.addEventListener("click", handleClick);
	return () => document.removeEventListener("click", handleClick);
});
</script>

<div class="lang-switcher" class:open={isOpen}>
	<button
		type="button"
		class="btn-plain scale-animation rounded-lg h-9 w-9 md:h-11 md:w-11 active:scale-90 flex items-center justify-center"
		onclick={(e) => {
			e.preventDefault();
			e.stopPropagation();
			toggle(e);
		}}
		title="切换语言 / Switch Language"
		aria-label="切换语言 / Switch Language"
		aria-haspopup="listbox"
		aria-expanded={isOpen}
	>
		<span class="lang-flag-wrapper" style="display:inline-flex;align-items:center;justify-content:center;line-height:0;">
			{#key $currentLang}
				{@html currentFlagSvg}
			{/key}
		</span>
	</button>
	{#if isOpen}
		<div class="lang-dropdown">
			{#each SUPPORTED_LANGS as lang}
				<button
					type="button"
					class="lang-option"
					class:active={$currentLang === lang.code}
					onclick={(e) => {
						e.preventDefault();
						e.stopPropagation();
						selectLang(lang.code);
					}}
				>
					<span class="flag-svg" style="display:inline-flex;align-items:center;line-height:0;">
						{@html FLAG_SVG[lang.code as Lang]}
					</span>
					<span class="lang-native">{lang.nativeLabel}</span>
					<span class="lang-eng">{lang.label}</span>
					{#if $currentLang === lang.code}
						<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
							<polyline points="20 6 9 17 4 12"></polyline>
						</svg>
					{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.lang-switcher {
		position: relative;
		display: inline-flex;
		align-items: center;
	}

	.lang-switcher .lang-flag-wrapper {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		user-select: none;
	}

	.lang-switcher .lang-dropdown {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		min-width: 200px;
		max-height: 320px;
		overflow-y: auto;
		background: var(--card-bg, #fff);
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		border: 1px solid var(--border, #ddd);
		border-radius: 14px;
		box-shadow: 0 10px 38px rgba(0, 0, 0, 0.16), 0 2px 6px rgba(0, 0, 0, 0.04);
		z-index: 1000;
		padding: 6px;
		animation: dropdownIn 0.18s cubic-bezier(0.16, 1, 0.3, 1);
		transform-origin: top right;
	}

	.lang-switcher .lang-dropdown .lang-option {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 10px 12px;
		border: none;
		background: transparent;
		color: var(--text-primary, inherit);
		cursor: pointer;
		transition: background 0.18s ease, color 0.18s ease;
		text-align: left;
		font-size: 14px;
		border-radius: 10px;
		position: relative;
	}

	.lang-switcher .lang-dropdown .lang-option:hover {
		background: color-mix(in srgb, var(--primary, #0066cc) 10%, transparent);
	}

	.lang-switcher .lang-dropdown .lang-option.active {
		color: var(--primary, #0066cc);
		background: color-mix(in srgb, var(--primary, #0066cc) 14%, transparent);
		font-weight: 600;
	}

	.lang-switcher .lang-dropdown .lang-option.active::before {
		content: "";
		position: absolute;
		left: 3px;
		top: 50%;
		transform: translateY(-50%);
		width: 3px;
		height: 60%;
		border-radius: 2px;
		background: var(--primary, #0066cc);
	}

	.lang-switcher .lang-dropdown .flag-svg {
		flex-shrink: 0;
	}

	.lang-switcher .lang-dropdown .lang-native {
		font-weight: 500;
		flex-shrink: 0;
	}

	.lang-switcher .lang-dropdown .lang-option.active .lang-native {
		font-weight: 700;
	}

	.lang-switcher .lang-dropdown .lang-eng {
		margin-left: auto;
		font-size: 12px;
		color: var(--text-tertiary, #999);
		opacity: 0.8;
	}

	.lang-switcher .lang-dropdown .lang-option svg {
		margin-left: auto;
		flex-shrink: 0;
	}

	.lang-switcher .lang-dropdown .lang-option.active svg {
		color: var(--primary, #0066cc);
	}

	/* Custom scrollbar for dropdown */
	.lang-switcher .lang-dropdown::-webkit-scrollbar {
		width: 6px;
	}
	.lang-switcher .lang-dropdown::-webkit-scrollbar-track {
		background: transparent;
	}
	.lang-switcher .lang-dropdown::-webkit-scrollbar-thumb {
		background: color-mix(in srgb, var(--primary, #0066cc) 20%, transparent);
		border-radius: 3px;
	}
	.lang-switcher .lang-dropdown::-webkit-scrollbar-thumb:hover {
		background: color-mix(in srgb, var(--primary, #0066cc) 35%, transparent);
	}

	@keyframes dropdownIn {
		from {
			opacity: 0;
			transform: translateY(-6px) scale(0.97);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}
</style>
