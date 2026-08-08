<script lang="ts">
import "@/styles/tokens-antd.css";
import { onMount } from "svelte";
import Icon from "@/components/common/Icon.svelte";
import {
	OOBE_LANGS,
	oobe,
	STEPS,
} from "@/composables/oobe/useOobeWizard.svelte";
import DatabaseStep from "./DatabaseStep.svelte";
import EnvCheckStep from "./EnvCheckStep.svelte";
import FeatureToggleStep from "./FeatureToggleStep.svelte";
import InstallStep from "./InstallStep.svelte";
import SiteAdminStep from "./SiteAdminStep.svelte";
import WelcomeStep from "./WelcomeStep.svelte";

onMount(() => {
	oobe.initOobe();
});

let _lastStepSeen = -1;
$: {
	const s = oobe.currentStep;
	if (_lastStepSeen !== s) {
		_lastStepSeen = s;
		if (
			typeof window !== "undefined" &&
			s > 1 &&
			oobe.backendReachable === "no"
		) {
			void oobe.checkBackendConnectivity(false);
		}
	}
}
</script>

<div class="oobe-shell" data-oobe-shell>

	{#if oobe.toast}
		<div class="o-toast o-toast-{oobe.toast.type}" role="status">
			<svg class="o-toast-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
				{#if oobe.toast.type === "success"}
					<path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM10 15.17L6.83 12L5.41 13.41L10 18L20.59 7.41L19.17 6L10 15.17Z" fill="currentColor"/>
				{:else if oobe.toast.type === "error"}
					<path d="M12 2C6.47 2 2 6.47 2 12C2 17.53 6.47 22 12 22C17.53 22 22 17.53 22 12C22 6.47 17.53 2 12 2ZM15.59 17L12 13.41L8.41 17L7 15.59L10.59 12L7 8.41L8.41 7L12 10.59L15.59 7L17 8.41L13.41 12L17 15.59L15.59 17Z" fill="currentColor"/>
				{:else}
					<path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V11H13V17ZM13 9H11V7H13V9Z" fill="currentColor"/>
				{/if}
			</svg>
			<span>{oobe.toast.msg}</span>
		</div>
	{/if}

	{#if oobe.backendReachable === "no"}
		<div class="o-offline" role="alert" aria-live="assertive">
			<div class="o-offline-card">
				<div class="o-offline-icon" aria-hidden="true">
					<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M19.35 10.04C18.67 6.59 15.64 4 12 4C10.45 4 9.01 4.43 7.8 5.2L9.28 6.68C10.09 6.15 11.01 5.84 12 5.84C14.37 5.84 16.47 7.21 17.41 9.21L19.35 10.04ZM12 19.85C14.04 19.85 15.87 19.03 17.19 17.71L18.67 19.19C16.94 20.95 14.63 22 12 22C7.59 22 3.86 19.41 2.38 15.67L4.51 14.78C5.54 17.4 8.51 19.85 12 19.85ZM4.27 5.97L2.86 7.38L5.11 9.63L4.27 10C4.69 11.02 5.34 11.95 6.16 12.73L7.6 14.17L8.78 12.99L7.46 11.68C7.43 11.65 7.39 11.62 7.36 11.59L4.27 5.97ZM15.94 12.55C15.65 11.91 15.21 11.33 14.67 10.83L12.81 8.97C12.61 8.77 12.38 8.6 12.14 8.46L9.88 6.2L12 4.08L14.36 6.44L15.94 12.55ZM21.61 7.38L20.2 5.97L18.07 9.76L14.36 13.47L13.19 12.3L11 14.49L14.57 18.06L16.44 16.19L17.19 16.94L18.73 15.4C19.92 14.16 20.81 12.62 21.32 10.9L21.61 7.38Z" fill="currentColor"/>
					</svg>
				</div>
				<div class="o-offline-tag">
					<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="o-tag-icon" aria-hidden="true">
						<path d="M11 7L9.6 8.4L13.2 12L9.6 15.6L11 17L16 12L11 7ZM12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" fill="currentColor"/>
					</svg>
					Back-end Unreachable
				</div>
				<h2 class="o-offline-title">连接不到后端服务器</h2>
				<p class="o-offline-lead">
					安装向导需要与后端 API (FastAPI) 通信，当前浏览器请求
					<code class="o-inline-code">{typeof window !== "undefined" ? (window.location.origin + "/api/oobe/status") : "/api/oobe/status"}</code>
					失败。
				</p>
				{#if oobe.backendLastError}
					<div class="o-offline-reason">
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="o-reason-icon" aria-hidden="true">
							<path d="M11 7L9.6 8.4L13.2 12L9.6 15.6L11 17L16 12L11 7ZM12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" fill="currentColor"/>
						</svg>
						<span>{oobe.backendLastError}</span>
					</div>
				{/if}

				<ul class="o-offline-list">
					<li>
						<span class="o-offline-list-dot" />
						<span><strong>确认后端已启动</strong>：请在后端目录执行 <code class="o-inline-code">python -m uvicorn main:app --port 8000 --reload</code>（或等价启动命令），默认监听 <code class="o-inline-code">http://localhost:8000</code>。</span>
					</li>
					<li>
						<span class="o-offline-list-dot" />
						<span><strong>核对前端代理配置</strong>：开发模式下，前端会通过 <code class="o-inline-code">Vite</code> 代理把 <code class="o-inline-code">/api/*</code> 转发到后端端口（默认为 <code class="o-inline-code">8000</code>）。若后端使用了其他端口，请在 <code class="o-inline-code">frontend/.env</code> 中设置 <code class="o-inline-code">API_BASE_URL</code>。</span>
					</li>
					<li>
						<span class="o-offline-list-dot" />
						<span><strong>防火墙 / HTTPS</strong>：确认本机没有拦截 8000 端口；若部署到 HTTPS 域名，确保后端启用了 SSL 或位于反向代理之后。</span>
					</li>
				</ul>

				<div class="o-offline-actions">
					<button
						type="button"
						class="o-btn o-btn-primary"
						on:click={() => oobe.checkBackendConnectivity(true)}
						disabled={oobe.backendCheckLoading}
					>
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class:o-spin={oobe.backendCheckLoading} aria-hidden="true">
							<path d="M17.65 6.35C16.2 4.9 14.21 4 12 4C7.58 4 4.01 7.58 4.01 12C4.01 16.42 7.58 20 12 20C15.73 20 18.84 17.45 19.73 14H17.65C16.83 16.33 14.61 18 12 18C8.69 18 6 15.31 6 12C6 8.69 8.69 6 12 6C13.66 6 15.14 6.69 16.22 7.78L13 11H20V4L17.65 6.35Z" fill="currentColor"/>
						</svg>
						{oobe.backendCheckLoading ? "正在重试…" : "重新连接"}
					</button>
					<a href="/" class="o-btn o-btn-default">
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
							<path d="M10 20V14H14V20H19V12H22L12 3L2 12H5V20H10Z" fill="currentColor"/>
						</svg>
						返回首页
					</a>
				</div>

				<details class="o-offline-details">
					<summary>诊断提示</summary>
					<div class="o-offline-details-body">
						<p>你可以先在终端里手动测试后端：</p>
						<pre class="o-code-block">curl -I "http://localhost:8000/api/oobe/status"</pre>
						<p>如果返回 <code class="o-inline-code">200 OK</code>，说明后端本身正常，排查重点放在 <strong>前端代理</strong> 或 <strong>CORS</strong>。</p>
					</div>
				</details>
			</div>
		</div>
	{:else}

		<header class="o-topbar">
			<div class="o-topbar-left">
				<a class="o-brand-mini" href="/" title="返回首页">
					<img src="/favicon/rosetta-primary-icon.png" alt="" />
					<span>Rosetta</span>
				</a>
			</div>
			<div class="o-topbar-pill" role="toolbar" aria-label="显示与语言设置">

				<div class="o-pop" data-oobe-lang-wrap>
					<button
						type="button"
						class="o-icon-btn o-lang-btn"
						title="切换语言"
						aria-haspopup="menu"
						aria-expanded={oobe.langPanelOpen}
						on:click={(e) => { e.stopPropagation(); oobe.langPanelOpen = !oobe.langPanelOpen; }}
					>
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
							<path d="M11.99 2C6.47 2 2 6.48 2 12C2 17.52 6.47 22 11.99 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 11.99 2ZM12 20C7.58 20 4 16.42 4 12C4 7.58 7.58 4 12 4C16.42 4 20 7.58 20 12C20 16.42 16.42 20 12 20ZM18.92 11H17.38C17.29 9.92 17.03 8.88 16.62 7.92L18.04 6.5C18.62 7.78 18.89 9.1 18.92 11ZM15.5 5.32L14.08 6.74C13.04 6.32 11.96 6.08 10.86 6.04L10.5 4H13.5C14.24 4.5 14.91 5.13 15.5 5.32ZM8.03 5.32C8.62 5.13 9.29 4.5 10.03 4H13.03L12.67 6.04C11.57 6.08 10.49 6.32 9.45 6.74L8.03 5.32ZM5.04 6.5C5.62 7.78 5.89 9.1 5.92 11H4.38C4.41 9.1 4.68 7.78 5.04 6.5ZM4.38 13H5.92C5.89 14.08 6.15 15.12 6.56 16.08L5.04 17.5C4.46 16.22 4.19 14.9 4.38 13ZM8.03 18.68C7.44 18.87 6.77 19.5 6.03 20H3.03L3.39 17.96C4.49 17.92 5.57 17.68 6.61 17.26L8.03 18.68ZM12.03 20C12.77 19.5 13.44 18.87 14.03 18.68L15.45 20.09C14.33 20.64 13.16 20.96 12.03 20H12.03ZM15.96 17.26C17 16.84 18.08 16.6 19.18 16.56L19.54 18.6H16.54C15.8 18.1 15.13 17.47 14.54 17.28L15.96 17.26ZM17.38 13H18.92C18.89 14.9 18.62 16.22 18.04 17.5L16.62 16.08C17.03 15.12 17.29 14.08 17.38 13ZM13.73 11.35H10.27L9.27 14.5H14.73L13.73 11.35ZM13.37 8.5H10.63L10.13 7H13.87L13.37 8.5Z" fill="currentColor"/>
						</svg>
						<span class="o-lang-tag">{oobe.currentLangShort()}</span>
					</button>
					{#if oobe.langPanelOpen}
					<div class="o-pop-panel" role="menu" aria-label="语言选择">
						{#each OOBE_LANGS as L}
							<button
								type="button"
								role="menuitemradio"
								aria-checked={L.code === oobe.currentLang}
								class="o-pop-item"
								class:o-pop-item-active={L.code === oobe.currentLang}
								data-lang={L.code}
								on:click={() => oobe.applyLang(L.code, true)}
							>
								<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="o-pop-icon" aria-hidden="true">
									<path d="M11.99 2C6.47 2 2 6.48 2 12C2 17.52 6.47 22 11.99 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 11.99 2ZM12 20C7.58 20 4 16.42 4 12C4 7.58 7.58 4 12 4C16.42 4 20 7.58 20 12C20 16.42 16.42 20 12 20ZM12.47 4.76C12.05 6.06 11.78 7.41 11.7 8.79H12.3C12.38 7.41 12.65 6.06 13.07 4.76C12.87 4.72 12.67 4.7 12.47 4.76ZM12 18.97C10.4 17.16 8.97 14.25 9.03 12.06H14.97C15.03 14.25 13.6 17.16 12 18.97ZM5.16 11.05C5.12 10.71 5.1 10.36 5.1 10.01C5.1 9.66 5.12 9.31 5.16 8.97H8.55C8.53 9.31 8.52 9.66 8.52 10.01C8.52 10.36 8.53 10.71 8.55 11.05H5.16ZM9.34 8.79H5.38C5.53 8.14 5.81 7.51 6.21 6.92L7.77 8.57C7.6 8.63 7.47 8.72 7.34 8.79H9.34ZM5.38 11.25H9.34C7.47 11.25 6.21 11.17 5.38 11.25ZM6.21 13.1C5.81 12.52 5.53 11.89 5.38 11.25H9.34C7.47 11.33 6.21 13.1 6.21 13.1ZM7.77 11.45L6.21 13.1C5.81 12.52 5.53 11.89 5.38 11.25H8.55C8.53 11.38 8.52 11.54 8.49 11.69L7.77 11.45ZM9.03 11.05C9.05 10.71 9.07 10.37 9.13 10.04H9.12C9.18 10.37 9.2 10.71 9.22 11.05H9.03ZM12 3.98C13.6 5.79 15.03 8.7 14.97 10.89H9.03C8.97 8.7 10.4 5.79 12 3.98ZM14.85 12.87L15.22 13.24L16.23 12.23L16.59 12.6L15.58 13.61L15.95 13.98L18.97 10.96L18.61 10.6L14.85 12.87ZM14.22 11.05H18.84C18.88 10.71 18.9 10.36 18.9 10.01C18.9 9.66 18.88 9.31 18.84 8.97H15.45C15.47 9.31 15.48 9.66 15.48 10.01C15.48 10.36 15.47 10.71 15.45 11.05H14.22ZM17.79 13.1C17.51 13.47 17.2 13.8 16.84 14.09L14.54 11.79C14.87 11.56 15.17 11.31 15.45 11.05H18.62C18.47 11.69 18.19 12.32 17.79 13.1ZM17.79 6.92C18.19 7.51 18.47 8.14 18.62 8.79H15.45C15.73 8.47 16.02 8.16 16.31 7.86C16.79 7.51 17.29 7.19 17.79 6.92ZM12.3 11.25H11.7C12.1 13.18 13.38 15.06 14.85 16.69C13.6 17.78 12.05 18.97 12 18.97C10.4 17.16 8.97 14.25 9.03 12.06H14.97C14.9 11.67 14.68 11.41 12.3 11.25Z" fill="currentColor"/>
								</svg>
								<span class="o-pop-label">{L.label}</span>
								{#if L.code === oobe.currentLang}
									<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="o-pop-check" aria-hidden="true">
										<path d="M9 16.17L4.83 12L3.41 13.41L9 19L21 7L19.59 5.59L9 16.17Z" fill="currentColor"/>
									</svg>
								{/if}
							</button>
						{/each}
					</div>
					{/if}
				</div>

				<button
					type="button"
					class="o-icon-btn o-theme-btn o-theme-cycle"
					title={oobe.modeTitle(oobe.themeMode)}
					aria-label="切换主题（亮色 / 暗色）"
					data-theme-mode={oobe.themeMode}
					on:click|stopPropagation={(e) => oobe.switchTheme(e)}
				>
					<span class="o-icon-stack" aria-hidden="true">
						<svg
							class="o-icon-layer"
							class:o-icon-layer-active={oobe.themeMode === "light"}
							viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"
						>
							<path d="M12 7C9.24 7 7 9.24 7 12C7 14.76 9.24 17 12 17C14.76 17 17 14.76 17 12C17 9.24 14.76 7 12 7ZM12 15C10.34 15 9 13.66 9 12C9 10.34 10.34 9 12 9C13.66 9 15 10.34 15 12C15 13.66 13.66 15 12 15ZM11 1H13V4H11V1ZM11 20H13V23H11V20ZM4.22 5.64L5.64 4.22L7.76 6.34L6.34 7.76L4.22 5.64ZM16.24 18.36L17.66 16.94L19.78 19.06L18.36 20.48L16.24 18.36ZM1 13H4V11H1V13ZM20 13H23V11H20V13ZM4.22 19.78L6.34 17.66L7.76 19.08L5.64 21.2L4.22 19.78ZM16.24 6.68L17.66 5.26L19.78 7.38L18.36 8.8L16.24 6.68Z" fill="#faad14"/>
						</svg>
						<svg
							class="o-icon-layer"
							class:o-icon-layer-active={oobe.themeMode === "dark"}
							viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"
						>
							<path d="M9.37 5.51C11.68 3.87 14.68 3.27 17.32 4.18C17.67 4.3 17.81 4.73 17.7 5.08C17.58 5.43 17.15 5.57 16.8 5.45C14.78 4.72 12.52 5.27 10.7 6.82C8.94 8.34 7.94 10.71 8.04 13.13C8.09 14.32 8.5 15.49 9.21 16.44C10.4 18.06 12.4 19.03 14.49 19C15.73 18.98 16.93 18.61 17.92 17.94C18.22 17.73 18.64 17.82 18.84 18.12C19.04 18.43 18.95 18.85 18.64 19.05C17.35 19.93 15.85 20.47 14.29 20.61C11.75 20.86 9.27 20.12 7.36 18.58C5.37 16.95 4.08 14.44 3.9 11.73C3.71 8.84 4.87 6.03 6.91 4.08C7.25 3.75 7.76 3.76 8.08 4.1C8.4 4.43 8.4 4.94 8.08 5.26C8.01 5.33 7.94 5.41 7.88 5.48L9.37 5.51ZM19.71 7.53C20.1 7.14 20.74 7.14 21.12 7.53C21.51 7.92 21.51 8.55 21.12 8.94L19.54 10.52C19.15 10.91 18.51 10.91 18.12 10.52C17.73 10.13 17.73 9.5 18.12 9.11L19.71 7.53Z" fill="#7b87d1"/>
						</svg>
					</span>
				</button>

			</div>
		</header>

		<main class="o-card" role="main" aria-label="安装向导">

			<header class="o-header">
				<div class="o-brand">
					<div class="o-brand-logo" aria-hidden="true">
						<img src="/favicon/rosetta-primary-icon.png" alt="Rosetta" />
					</div>
					<div class="o-brand-text">
						<div class="o-brand-tagline">
							<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="o-tagline-icon" aria-hidden="true">
								<path d="M19 9L17.59 7.59L16.32 10.68L12 6.36L10.35 8L11.64 9.29L5.64 15.29L7.05 16.7L13.05 10.7L14.36 12L12.69 13.64L17.01 18L18.66 16.36L14.34 12L17.43 8.73L20.41 11.71L22 10.12L19 9ZM9 20H15V22H9V20Z" fill="#1677ff"/>
							</svg>
							Installation Wizard
						</div>
						<h1 class="o-brand-title">Rosetta 博客系统</h1>
						<p class="o-brand-sub">只需六步，搭建属于你的创作空间</p>
					</div>
				</div>

				<ol class="o-stepper" aria-label="安装步骤">
					{#each STEPS as name, i}
						{@const stepIdx = i + 1}
						{@const done = stepIdx < oobe.currentStep}
						{@const active = stepIdx === oobe.currentStep}
						<li class="o-stepper-item" class:o-stepper-done={done} class:o-stepper-active={active}>
							<div class="o-stepper-node">
								<button
									type="button"
									class="o-stepper-dot"
									aria-current={active ? "step" : undefined}
									on:click={() => done && oobe.goStep(stepIdx)}
									disabled={stepIdx > oobe.currentStep}
									title={done ? `返回：${name}` : active ? `当前步骤：${name}` : `未解锁：${name}`}
								>
									{#if done}
										<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="o-step-check" aria-hidden="true">
											<path d="M9 16.17L4.83 12L3.41 13.41L9 19L21 7L19.59 5.59L9 16.17Z" fill="currentColor"/>
										</svg>
									{:else}
										<span class="o-step-num">{stepIdx}</span>
									{/if}
								</button>
								<div class="o-stepper-content">
									<div class="o-stepper-title">{name}</div>
									<div class="o-stepper-desc">Step {stepIdx} / {STEPS.length}</div>
								</div>
							</div>
							{#if i < STEPS.length - 1}
								<div class="o-stepper-rail" class:o-stepper-rail-done={done} aria-hidden="true">
									<div class="o-stepper-rail-fill"></div>
								</div>
							{/if}
						</li>
					{/each}
				</ol>
			</header>

			<section
				class="o-step"
				class:o-step-in={oobe.stepVisible}
				class:o-step-next={oobe.animDir === "next"}
				class:o-step-prev={oobe.animDir === "prev"}
			>

				{#if oobe.currentStep === 1}
					<WelcomeStep on:quick={() => void oobe.quickInstall()} installing={oobe.installing || !!oobe.installResult} />
				{:else if oobe.currentStep === 2}
					<EnvCheckStep />
				{:else if oobe.currentStep === 3}
					<DatabaseStep />
				{:else if oobe.currentStep === 4}
					<SiteAdminStep />
				{:else if oobe.currentStep === 5}
					<FeatureToggleStep />
				{:else if oobe.currentStep === 6}
					<InstallStep />
				{/if}
			</section>

			<footer class="o-actions">
				{#if oobe.currentStep > 1 && oobe.currentStep < 6}
					<button type="button" class="o-btn o-btn-default" on:click={() => oobe.back()} disabled={(oobe.currentStep === 6 && oobe.installing) || oobe.backendReachable === "no"}>
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
							<path d="M20 11H7.83L13.42 5.41L12 4L4 12L12 20L13.41 18.59L7.83 13H20V11Z" fill="currentColor"/>
						</svg>
						上一步
					</button>
				{/if}
				<div class="o-actions-spacer"></div>
				{#if oobe.currentStep === 1}
					<button
						type="button"
						class="o-btn o-btn-primary"
						on:click={async () => {
							try {
								if (oobe.backendReachable !== "yes") {
									const ok = await oobe.checkBackendConnectivity(true);
									if (!ok) {
										oobe.showToast("error", oobe.backendLastError || "后端服务器未连接，先启动后端再开始安装");
										return;
									}
								}
								oobe.next();
							} catch (e: any) {
								oobe.showToast("error", e?.message || "进入下一步失败，请重试");
							}
						}}
						disabled={oobe.backendCheckLoading || oobe.backendReachable === "no"}
					>
						{#if oobe.backendCheckLoading}
							<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="o-spin" aria-hidden="true">
								<path d="M17.65 6.35C16.2 4.9 14.21 4 12 4C7.58 4 4.01 7.58 4.01 12C4.01 16.42 7.58 20 12 20C15.73 20 18.84 17.45 19.73 14H17.65C16.83 16.33 14.61 18 12 18C8.69 18 6 15.31 6 12C6 8.69 8.69 6 12 6C13.66 6 15.14 6.69 16.22 7.78L13 11H20V4L17.65 6.35Z" fill="currentColor"/>
							</svg>
							检测后端中…
						{:else}
							开始安装
							<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
								<path d="M12 4L10.59 5.41L16.17 11H4V13H16.17L10.59 18.59L12 20L20 12L12 4Z" fill="currentColor"/>
							</svg>
						{/if}
					</button>
				{:else if oobe.currentStep === 2}
					<button type="button" class="o-btn o-btn-default" on:click={() => oobe.runEnvCheck()} disabled={oobe.envLoading || oobe.backendReachable === "no"}>
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
							<path d="M17.65 6.35C16.2 4.9 14.21 4 12 4C7.58 4 4.01 7.58 4.01 12C4.01 16.42 7.58 20 12 20C15.73 20 18.84 17.45 19.73 14H17.65C16.83 16.33 14.61 18 12 18C8.69 18 6 15.31 6 12C6 8.69 8.69 6 12 6C13.66 6 15.14 6.69 16.22 7.78L13 11H20V4L17.65 6.35Z" fill="currentColor"/>
						</svg>
						重新检测
					</button>
					<button type="button" class="o-btn o-btn-primary" on:click={() => oobe.next()} disabled={oobe.backendReachable === "no"}>
						下一步
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
							<path d="M12 4L10.59 5.41L16.17 11H4V13H16.17L10.59 18.59L12 20L20 12L12 4Z" fill="currentColor"/>
						</svg>
					</button>
				{:else if oobe.currentStep < 5}
					<button type="button" class="o-btn o-btn-primary" on:click={() => oobe.next()} disabled={oobe.backendReachable === "no"}>
						下一步
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
							<path d="M12 4L10.59 5.41L16.17 11H4V13H16.17L10.59 18.59L12 20L20 12L12 4Z" fill="currentColor"/>
						</svg>
					</button>
				{:else if oobe.currentStep === 5}
					<button
						type="button"
						class="o-btn o-btn-primary"
						on:click={() => {
							try {
								if (!oobe.validateSiteAdmin()) {
									oobe.showToast("error", "请先完善站点信息和管理员账户");
									void oobe.goStep(4);
									return;
								}
								if (oobe.backendReachable !== "yes") {
									oobe.showToast("error", oobe.backendLastError || "后端服务器未连接，无法开始安装");
									return;
								}
								void oobe.goStep(6);
								requestAnimationFrame(() => {
									void oobe.startInstall();
								});
							} catch (e: any) {
								oobe.showToast("error", e?.message || "启动安装失败，请重试");
							}
						}}
						disabled={oobe.backendReachable !== "yes" || oobe.installing}
					>
						<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class:o-spin={oobe.installing} aria-hidden="true">
							{#if oobe.installing}
								<path d="M17.65 6.35C16.2 4.9 14.21 4 12 4C7.58 4 4.01 7.58 4.01 12C4.01 16.42 7.58 20 12 20C15.73 20 18.84 17.45 19.73 14H17.65C16.83 16.33 14.61 18 12 18C8.69 18 6 15.31 6 12C6 8.69 8.69 6 12 6C13.66 6 15.14 6.69 16.22 7.78L13 11H20V4L17.65 6.35Z" fill="currentColor"/>
							{:else}
								<path d="M8 5V19L19 12L8 5Z" fill="currentColor"/>
							{/if}
						</svg>
						{oobe.installing ? "安装中…" : "开始安装"}
					</button>
				{/if}
			</footer>

		</main>
	{/if}
</div>

<style>
.oobe-shell {
	--antd-shadow-md: 0 4px 16px 0 rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.06);

	position: relative;
	min-height: 100vh;
	width: 100%;
	padding: 24px 16px 40px;
	display: flex;
	flex-direction: column;
	align-items: center;
	overflow-x: hidden;
	background-color: var(--antd-color-bg-body, #f5f5f5);
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
	-webkit-font-smoothing: antialiased;
	-moz-osx-font-smoothing: grayscale;
	box-sizing: border-box;
}
.oobe-shell *, .oobe-shell *::before, .oobe-shell *::after { box-sizing: border-box; }
:global(html.dark) .oobe-shell {
	background-color: var(--antd-color-bg-body, #0a0a0a);
	color: var(--antd-color-text, rgba(255, 255, 255, 0.88));
}

.o-spin {
	animation: o-spin-anim 1s linear infinite;
}
@keyframes o-spin-anim {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}

/* ========== Toast ========== */
.o-toast {
	position: fixed; top: 20px; right: 20px; z-index: 9999;
	display: inline-flex; align-items: center; gap: 8px;
	padding: 9px 16px; border-radius: 4px;
	font-size: 14px; font-weight: 400;
	box-shadow: 0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12);
	animation: o-toast-in 0.2s cubic-bezier(0.215, 0.61, 0.355, 1) both;
}
.o-toast-icon { width: 16px; height: 16px; flex-shrink: 0; }
.o-toast-success { background: #fff; color: #52c41a; border: 1px solid #b7eb8f; }
.o-toast-error   { background: #fff; color: #ff4d4f; border: 1px solid #ffa39e; }
.o-toast-info    { background: #fff; color: #1677ff; border: 1px solid #91caff; }
@keyframes o-toast-in {
	from { opacity: 0; transform: translateY(-8px); }
	to   { opacity: 1; transform: translateY(0); }
}

/* ========== 后端失联：离线卡片 ========== */
.o-offline {
	position: relative; z-index: 2;
	width: 100%; max-width: 820px;
	padding: 24px 16px 32px;
	display: flex; align-items: stretch; justify-content: center;
}
.o-offline-card {
	width: 100%;
	background: #fff;
	border: 1px solid #ffa39e;
	border-radius: 8px;
	box-shadow: var(--antd-shadow-md);
	padding: 24px;
	display: flex; flex-direction: column; gap: 16px;
}
:global(html.dark) .o-offline-card {
	background: var(--antd-color-bg-surface, #141414);
}
.o-offline-icon {
	align-self: flex-start;
	width: 48px; height: 48px; border-radius: 8px;
	display: inline-flex; align-items: center; justify-content: center;
	background: #fff2f0;
	border: 1px solid #ffccc7;
	color: #ff4d4f;
}
.o-offline-icon :global(svg) { width: 24px; height: 24px; }

.o-offline-tag {
	align-self: flex-start;
	display: inline-flex; align-items: center; gap: 6px;
	padding: 2px 8px; border-radius: 4px;
	font-size: 12px; font-weight: 500;
	background: #fff2f0;
	color: #ff4d4f;
	border: 1px solid #ffccc7;
}
.o-tag-icon { width: 12px; height: 12px; }

.o-offline-title {
	margin: 0;
	font-size: 24px;
	font-weight: 600;
	line-height: 1.3;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
.o-offline-lead {
	margin: 0;
	font-size: 14px; line-height: 1.5714; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
	max-width: 72ch;
}
.o-inline-code {
	display: inline-block;
	padding: 0 6px;
	border-radius: 4px;
	font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
	font-size: 12.5px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	color: #d4380d;
	word-break: break-all;
}
.o-offline-reason {
	display: inline-flex; align-items: center; gap: 8px; align-self: flex-start;
	padding: 8px 12px; border-radius: 6px;
	background: #fff2f0;
	border: 1px solid #ffccc7;
	color: #ff4d4f;
	font-size: 13px; font-weight: 500;
}
.o-reason-icon { width: 16px; height: 16px; flex-shrink: 0; }

.o-offline-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }
.o-offline-list li { display: flex; align-items: flex-start; gap: 12px; }
.o-offline-list-dot {
	flex-shrink: 0;
	width: 6px; height: 6px; margin-top: 8px; border-radius: 50%;
	background: #1677ff;
}
.o-offline-list strong { font-weight: 600; color: var(--antd-color-text, rgba(0, 0, 0, 0.88)); }
.o-offline-list span:not(.o-offline-list-dot) {
	font-size: 14px; line-height: 1.5714; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}

.o-offline-actions {
	display: inline-flex; align-items: center; gap: 12px; flex-wrap: wrap;
	padding-top: 4px;
}

.o-offline-details {
	border-radius: 8px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	overflow: hidden;
	margin-top: 4px;
}
.o-offline-details summary {
	cursor: pointer;
	padding: 12px 16px;
	font-size: 14px; font-weight: 500; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
	list-style: none;
}
.o-offline-details summary::-webkit-details-marker { display: none; }
.o-offline-details-body {
	padding: 4px 16px 16px;
	display: flex; flex-direction: column; gap: 12px;
}
.o-offline-details-body p { margin: 0; font-size: 14px; line-height: 1.5714; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65)); }
.o-code-block {
	margin: 0;
	padding: 12px 16px;
	border-radius: 6px;
	background: #1f1f1f; color: #e8e8e8; border: 1px solid #333;
	font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
	font-size: 12px; line-height: 1.5;
	white-space: pre-wrap; word-break: break-word;
}

/* ========== 顶部工具条 ========== */
.o-topbar {
	position: relative; z-index: 5;
	width: 100%; max-width: 1060px; margin: 0 auto 24px;
	display: flex; align-items: center; justify-content: space-between;
}
.o-topbar-left { display: flex; align-items: center; }
.o-brand-mini {
	display: inline-flex; align-items: center; gap: 8px;
	text-decoration: none; color: inherit;
	padding: 4px 8px; border-radius: 4px;
	font-weight: 600; font-size: 14px;
}
.o-brand-mini img { width: 20px; height: 20px; }

.o-topbar-pill {
	display: inline-flex; align-items: center; gap: 4px;
	padding: 4px; border-radius: 4px;
	background: var(--antd-color-bg-surface, #ffffff);
	border: 1px solid var(--antd-color-border, #d9d9d9);
	box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
}
:global(html.dark) .o-topbar-pill {
	background: var(--antd-color-bg-surface, #141414);
}
.o-icon-btn {
	position: relative;
	width: 32px; height: 32px; min-width: 32px;
	border-radius: 4px;
	display: inline-flex; align-items: center; justify-content: center;
	gap: 6px;
	border: none; background: transparent;
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65)); cursor: pointer;
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
	font-family: inherit;
}
.o-icon-btn :global(svg) { width: 16px; height: 16px; }
.o-icon-btn:hover {
	background: rgba(0, 0, 0, 0.06);
	color: #1677ff;
}
.o-icon-btn:active { transform: scale(0.96); }
.o-lang-btn { width: auto; min-width: auto; padding: 0 11px 0 8px; border-radius: 4px; }
.o-lang-tag { font-size: 12px; font-weight: 500; line-height: 1; }

.o-theme-cycle .o-icon-stack {
  position: relative;
  width: 16px;
  height: 16px;
  display: inline-block;
}
.o-theme-cycle .o-icon-layer {
  position: absolute;
  inset: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  opacity: 0;
  transform: scale(0.85);
  transition:
    opacity 200ms cubic-bezier(0.645, 0.045, 0.355, 1),
    transform 200ms cubic-bezier(0.645, 0.045, 0.355, 1);
}
.o-theme-cycle .o-icon-layer.o-icon-layer-active {
  opacity: 1;
  transform: scale(1);
}

/* Popover */
.o-pop { position: relative; }
.o-pop-panel {
	position: absolute; z-index: 200;
	top: calc(100% + 8px); right: 0;
	min-width: 210px;
	padding: 4px;
	border-radius: 8px;
	background: var(--antd-color-bg-surface, #ffffff);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	box-shadow: 0 6px 24px 0 rgba(0, 0, 0, 0.12), 0 3px 6px -4px rgba(0, 0, 0, 0.06);
	animation: o-pop-in 0.15s cubic-bezier(0.215, 0.61, 0.355, 1) both;
}
:global(html.dark) .o-pop-panel {
	background: var(--antd-color-bg-surface, #141414);
}
@keyframes o-pop-in {
	from { opacity: 0; transform: translateY(-4px) scale(0.99); }
	to   { opacity: 1; transform: translateY(0) scale(1); }
}
.o-pop-item {
	width: 100%;
	display: inline-flex; align-items: center; gap: 10px;
	padding: 8px 12px;
	border-radius: 4px;
	border: none; background: transparent;
	font-size: 14px; font-weight: 400; color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	text-align: left; cursor: pointer;
	transition: background 0.15s ease, color 0.15s ease;
	font-family: inherit;
}
.o-pop-icon { width: 14px; height: 14px; flex-shrink: 0; color: #1677ff; opacity: 0.9; }
.o-pop-label { flex: 1; }
.o-pop-check { width: 14px; height: 14px; margin-left: auto; color: #1677ff; }
.o-pop-item:hover { background: rgba(0, 0, 0, 0.06); color: #1677ff; }
.o-pop-item-active { background: #e6f4ff; color: #1677ff; font-weight: 500; }

/* ========== 主卡片 ========== */
.o-card {
	position: relative; z-index: 1;
	width: 100%; max-width: 1060px;
	background: var(--antd-color-bg-surface, #ffffff);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	border-radius: 8px;
	box-shadow: var(--antd-shadow-md);
	overflow: hidden;
	display: flex; flex-direction: column;
	animation: o-card-in 0.3s cubic-bezier(0.215, 0.61, 0.355, 1) both;
}
@keyframes o-card-in {
	from { opacity: 0; transform: translateY(12px); }
	to   { opacity: 1; transform: translateY(0); }
}

/* ========== Header — 品牌与进度条分行 ========== */
.o-header {
	padding: 24px 24px 0;
	display: flex;
	flex-direction: column;
	align-items: stretch;
	gap: 24px;
}
@media (max-width: 720px) {
	.o-header { gap: 20px; padding: 20px 16px 0; }
}

.o-brand {
	display: flex; align-items: center; gap: 12px;
	padding: 0;
}
.o-brand-logo {
	width: 48px; height: 48px; border-radius: 8px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	display: inline-flex; align-items: center; justify-content: center;
	flex-shrink: 0;
}
.o-brand-logo img { width: 64%; height: 64%; object-fit: contain; }
.o-brand-text { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.o-brand-tagline {
	display: inline-flex; align-items: center; gap: 6px;
	font-size: 12px; font-weight: 500;
	color: #1677ff;
}
.o-tagline-icon { width: 14px; height: 14px; }
.o-brand-title {
	margin: 0; font-size: 22px; font-weight: 600; line-height: 1.3;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
.o-brand-sub {
	margin: 0; font-size: 14px; color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45)); font-weight: 400;
}

/* ========== Stepper（Ant Design 风格水平步骤条） ========== */
.o-stepper {
	list-style: none; padding: 16px 0 24px; margin: 0;
	display: flex; align-items: flex-start;
	overflow-x: auto;
	border-top: 1px solid var(--antd-color-split, #f0f0f0);
}
.o-stepper::-webkit-scrollbar { height: 4px; }
.o-stepper::-webkit-scrollbar-thumb { background: var(--antd-color-border, #d9d9d9); border-radius: 2px; }
.o-stepper-item {
	position: relative;
	flex: 1 1 0; min-width: 140px;
	display: flex; align-items: flex-start;
}
.o-stepper-node {
	display: flex; align-items: flex-start; gap: 12px;
	padding-right: 12px;
}
.o-stepper-dot {
	width: 32px; height: 32px; min-width: 32px;
	border-radius: 50%;
	border: 1px solid var(--antd-color-border, #d9d9d9);
	background: var(--antd-color-bg-surface, #ffffff);
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
	font-size: 14px; font-weight: 500; font-family: inherit;
	display: inline-flex; align-items: center; justify-content: center;
	cursor: pointer; padding: 0;
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
:global(html.dark) .o-stepper-dot {
	background: var(--antd-color-bg-surface, #141414);
}
.o-stepper-dot:disabled { cursor: not-allowed; }
.o-step-check { width: 14px; height: 14px; }
.o-step-num { font-size: 14px; line-height: 1; }
.o-stepper-done .o-stepper-dot {
	background: #52c41a;
	border-color: #52c41a;
	color: #fff;
}
.o-stepper-active .o-stepper-dot {
	background: #1677ff;
	border-color: #1677ff;
	color: #fff;
}
.o-stepper-content {
	display: flex; flex-direction: column; gap: 4px;
	min-width: 0;
	padding-top: 4px;
}
.o-stepper-title {
	font-size: 14px; font-weight: 500;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
	white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.o-stepper-desc {
	font-size: 12px;
	color: var(--antd-color-text-quaternary, rgba(0, 0, 0, 0.25));
}
.o-stepper-done .o-stepper-title,
.o-stepper-active .o-stepper-title {
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	font-weight: 600;
}
.o-stepper-done .o-stepper-desc,
.o-stepper-active .o-stepper-desc {
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}

.o-stepper-rail {
	position: absolute;
	top: 16px;
	left: calc(32px + 12px + 12px);
	right: 0;
	height: 1px;
	background: var(--antd-color-border, #d9d9d9);
	overflow: hidden;
}
.o-stepper-item:last-child .o-stepper-rail { display: none; }
.o-stepper-rail-fill {
	height: 100%;
	width: 0%;
	background: #52c41a;
	transition: width 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}
.o-stepper-rail-done .o-stepper-rail-fill {
	width: 100%;
}

/* ========== Step 内容容器 ========== */
.o-step {
	padding: 24px 24px 0;
	min-height: 460px;
	flex: 1;
}
@media (max-width: 640px) {
	.o-step { padding: 20px 16px 0; min-height: 400px; }
}
.o-step-in.o-step-next { animation: o-slide-next 0.2s cubic-bezier(0.215, 0.61, 0.355, 1) both; }
.o-step-in.o-step-prev { animation: o-slide-prev 0.2s cubic-bezier(0.215, 0.61, 0.355, 1) both; }
@keyframes o-slide-next { from { opacity: 0; transform: translateX(12px); } to { opacity: 1; transform: translateX(0); } }
@keyframes o-slide-prev { from { opacity: 0; transform: translateX(-12px); } to { opacity: 1; transform: translateX(0); } }

/* ========== 底部操作栏 ========== */
.o-actions {
	padding: 12px 24px 24px;
	display: flex; align-items: center; gap: 12px;
	margin-top: 24px;
	border-top: 1px solid var(--antd-color-split, #f0f0f0);
	background: transparent;
}
@media (max-width: 640px) { .o-actions { padding: 12px 16px 20px; } }
.o-actions-spacer { flex: 1; }

/* ========== 按钮（Ant Design 风格） ========== */
.o-btn {
	display: inline-flex; align-items: center; justify-content: center; gap: 6px;
	padding: 4px 15px;
	border-radius: 4px;
	border: 1px solid transparent;
	font-size: 14px; font-weight: 400; line-height: 1.5714;
	height: 32px;
	cursor: pointer;
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
	font-family: inherit;
	text-decoration: none; white-space: nowrap;
	user-select: none;
}
.o-btn :global(svg) { width: 14px; height: 14px; flex-shrink: 0; }
.o-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }

.o-btn-primary {
	background: #1677ff;
	color: #fff;
	border-color: #1677ff;
	box-shadow: 0 2px 0 rgba(5, 145, 255, 0.1);
}
.o-btn-primary:hover:not(:disabled) {
	background: #4096ff;
	border-color: #4096ff;
}
.o-btn-primary:active:not(:disabled) {
	background: #0958d9;
	border-color: #0958d9;
}

.o-btn-default {
	background: var(--antd-color-bg-surface, #ffffff);
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	border-color: var(--antd-color-border, #d9d9d9);
}
.o-btn-default:hover:not(:disabled) {
	background: #ffffff;
	color: #4096ff;
	border-color: #4096ff;
}
.o-btn-default:active:not(:disabled) {
	background: #ffffff;
	color: #0958d9;
	border-color: #0958d9;
}

.o-btn-outline {
	background: transparent;
	color: #1677ff;
	border-color: #1677ff;
}
.o-btn-outline:hover:not(:disabled) {
	background: transparent;
	color: #4096ff;
	border-color: #4096ff;
}

.o-btn-sm { padding: 0 7px; font-size: 12px; height: 24px; border-radius: 4px; gap: 4px; }
.o-btn-sm :global(svg) { width: 12px; height: 12px; }

.o-btn-block {
	width: 100%;
	margin-top: 12px;
}

/* ========== 共享：步骤内容卡片基础样式（子步骤复用） ========== */
:global(.o-step-inner) { display: flex; flex-direction: column; gap: 24px; width: 100%; }
:global(.o-step-head) { display: flex; flex-direction: column; gap: 8px; }
:global(.o-step-tag) {
	display: inline-flex; align-items: center; gap: 6px; align-self: flex-start;
	padding: 2px 8px; border-radius: 4px;
	font-size: 12px; font-weight: 500;
	background: #e6f4ff;
	color: #1677ff;
	border: 1px solid #91caff;
}
:global(.o-step-tag :global(svg)) { width: 12px; height: 12px; }
:global(.o-step-tag-soft) {
	background: var(--antd-color-bg-spot, #fafafa);
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
	border-color: var(--antd-color-border, #d9d9d9);
}
:global(.o-step-tag-pulse) {
	animation: o-pulse-soft 2s ease-in-out infinite;
}
@keyframes o-pulse-soft {
	0%, 100% { box-shadow: 0 0 0 0 rgba(22, 119, 255, 0.18); }
	50% { box-shadow: 0 0 0 6px rgba(22, 119, 255, 0); }
}
:global(.o-h2) {
	margin: 0;
	font-size: 24px;
	font-weight: 600;
	line-height: 1.3;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
:global(.o-h2.o-center) { text-align: center; }
:global(.o-lead) {
	margin: 0;
	font-size: 14px; line-height: 1.5714; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
	max-width: 76ch;
}
:global(.o-lead.o-center) { text-align: center; max-width: 60ch; margin: 0 auto; }
:global(.o-center) { text-align: center; }

/* ========== 共享：Callout ========== */
:global(.o-callout) {
	display: flex; align-items: flex-start; gap: 12px;
	padding: 12px 16px;
	border-radius: 6px;
	background: #fffbe6;
	border: 1px solid #ffe58f;
	margin-top: 16px;
}
:global(.o-callout :global(svg)) { width: 16px; height: 16px; flex-shrink: 0; margin-top: 2px; color: #faad14; }
:global(.o-callout-body) { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
:global(.o-callout-body strong) { font-size: 14px; font-weight: 600; color: var(--antd-color-text, rgba(0, 0, 0, 0.88)); }
:global(.o-callout-body p) { margin: 0; font-size: 14px; line-height: 1.5714; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65)); word-break: break-word; }

:global(.o-callout-error) {
	background: #fff2f0;
	border-color: #ffccc7;
}
:global(.o-callout-error :global(svg)) { color: #ff4d4f; }
:global(.o-callout-error .o-callout-body strong) { color: var(--antd-color-text, rgba(0, 0, 0, 0.88)); }

:global(.o-callout-warn) {
	background: #fffbe6;
	border-color: #ffe58f;
}
:global(.o-callout-warn :global(svg)) { color: #faad14; }
:global(.o-callout-warn .o-callout-body strong) { color: var(--antd-color-text, rgba(0, 0, 0, 0.88)); }

:global(.o-callout-info) {
	background: #e6f4ff;
	border-color: #91caff;
}
:global(.o-callout-info :global(svg)) { color: #1677ff; }
:global(.o-callout-info .o-callout-body strong) { color: var(--antd-color-text, rgba(0, 0, 0, 0.88)); }

/* ========== 共享：表单字段 ========== */
:global(.o-form-card) {
	padding: 20px;
	border-radius: 8px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	display: flex;
	flex-direction: column;
	gap: 16px;
}
:global(.o-form-card-head) {
	display: inline-flex; align-items: center; gap: 8px;
	font-size: 14px; font-weight: 500;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
:global(.o-form-card-head :global(svg)) { width: 16px; height: 16px; color: #1677ff; }
:global(.o-form-grid) {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16px 24px;
}
:global(.o-form-inner) {
	margin-top: 16px;
	padding-top: 16px;
	border-top: 1px dashed var(--antd-color-border-light, #f0f0f0);
}
:global(.o-field) { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
:global(.o-field-full) { grid-column: 1 / -1; }
:global(.o-field label) {
	display: inline-flex; align-items: center; gap: 6px;
	font-size: 14px; font-weight: 400;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	line-height: 1.5714;
}
:global(.o-label-icon) { width: 14px; height: 14px; color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45)); }
:global(.o-req) { color: #ff4d4f; }
:global(.o-field input) {
	width: 100%;
	height: 32px;
	padding: 4px 11px;
	border-radius: 4px;
	border: 1px solid #d9d9d9;
	background: var(--antd-color-bg-surface, #ffffff);
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	font-size: 14px;
	font-weight: 400;
	line-height: 1.5714;
	font-family: inherit;
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
	outline: none;
	box-sizing: border-box;
}
:global(.o-field input::placeholder) {
	color: var(--antd-color-text-quaternary, rgba(0, 0, 0, 0.25));
}
:global(.o-field input:hover) {
	border-color: #4096ff;
}
:global(.o-field input:focus) {
	border-color: #1677ff;
	box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.1);
}
:global(.o-field input:disabled) {
	background: var(--antd-color-bg-spot, #fafafa);
	color: var(--antd-color-text-quaternary, rgba(0, 0, 0, 0.25));
	cursor: not-allowed;
}
:global(.o-field input.o-field-error),
:global(.o-field-error input) {
	border-color: #ff4d4f;
}
:global(.o-field input.o-field-error:focus),
:global(.o-field-error input:focus) {
	box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.1);
}
:global(.o-field-error) {
	margin: 0;
	font-size: 12px;
	line-height: 1.6667;
	color: #ff4d4f;
}
:global(.o-field-hint) {
	margin: 0;
	display: inline-flex; align-items: center; gap: 4px;
	font-size: 12px;
	line-height: 1.6667;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}
:global(.o-field-hint :global(svg)) { width: 12px; height: 12px; flex-shrink: 0; }
@media (max-width: 640px) {
	:global(.o-form-grid) { grid-template-columns: 1fr; }
}

/* ========== 共享：两列布局（站点信息 / 管理员） ========== */
:global(.o-cols) {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 24px;
}
:global(.o-col) {
	padding: 20px;
	border-radius: 8px;
	background: #fff;
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	box-shadow: var(--antd-shadow-md);
	display: flex;
	flex-direction: column;
	gap: 16px;
}
:global(.o-col-head) {
	display: flex; align-items: center; gap: 12px;
	padding-bottom: 16px;
	border-bottom: 1px solid var(--antd-color-split, #f0f0f0);
}
:global(.o-col-icon) {
	width: 40px; height: 40px; border-radius: 8px;
	display: inline-flex; align-items: center; justify-content: center;
	background: #e6f4ff;
	border: 1px solid #91caff;
	color: #1677ff;
	flex-shrink: 0;
}
:global(.o-col-icon :global(svg)) { width: 20px; height: 20px; }
:global(.o-col-icon-cyan) { background: #e6fffb; border-color: #87e8de; color: #13c2c2; }
:global(.o-col-icon-violet) { background: #f9f0ff; border-color: #d3adf7; color: #722ed1; }
:global(.o-col-title) {
	margin: 0;
	font-size: 16px; font-weight: 600;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
:global(.o-col-sub) {
	margin: 2px 0 0;
	font-size: 13px;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}
:global(.o-col-body) {
	display: flex;
	flex-direction: column;
	gap: 16px;
}
@media (max-width: 900px) {
	:global(.o-cols) { grid-template-columns: 1fr; }
}

/* ========== 共享：开关 ========== */
:global(.o-switch) {
	position: relative;
	min-width: 44px;
	height: 22px;
	border-radius: 11px;
	border: none;
	background: rgba(0, 0, 0, 0.25);
	cursor: pointer;
	padding: 0;
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
	flex-shrink: 0;
}
:global(.o-switch::after) {
	content: "";
	position: absolute;
	top: 2px;
	left: 2px;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	background: #fff;
	box-shadow: 0 2px 4px 0 rgba(0, 35, 11, 0.2);
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
:global(.o-switch-thumb) { display: none; }
:global(.o-switch-on) {
	background: #1677ff;
}
:global(.o-switch-on::after) {
	left: calc(100% - 2px - 18px);
}
:global(.o-switch:hover) {
	background: rgba(0, 0, 0, 0.35);
}
:global(.o-switch-on:hover) {
	background: #4096ff;
}

/* ========== 共享：Switch + Toggle Card ========== */
:global(.o-toggle-card) {
	padding: 16px 20px;
	border-radius: 8px;
	background: #fff;
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	box-shadow: var(--antd-shadow-md);
	display: flex;
	flex-direction: column;
	gap: 16px;
}
:global(.o-toggle-head) {
	display: flex; align-items: center; gap: 16px;
}
:global(.o-toggle-icon-wrap) {
	width: 40px; height: 40px; border-radius: 8px;
	display: inline-flex; align-items: center; justify-content: center;
	background: #fff7e6;
	border: 1px solid #ffd591;
	color: #fa8c16;
	flex-shrink: 0;
}
:global(.o-toggle-icon-wrap :global(svg)) { width: 20px; height: 20px; }
:global(.o-toggle-icon-redis) { background: #fff1f0; border-color: #ffccc7; color: #ff4d4f; }
:global(.o-toggle-text) { flex: 1; min-width: 0; }
:global(.o-toggle-title) {
	font-size: 15px; font-weight: 600;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
:global(.o-toggle-sub) {
	margin: 4px 0 0;
	font-size: 13px;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}

/* ========== 共享：功能开关列表 ========== */
:global(.o-toggle-grid) {
	list-style: none; padding: 0; margin: 0;
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}
:global(.o-toggle-list) {
	display: flex; align-items: center; gap: 12px;
	padding: 16px;
	border-radius: 8px;
	background: var(--antd-color-bg-surface, #fff);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
:global(.o-toggle-list:hover) {
	border-color: #91caff;
}
:global(.o-toggle-list-on) {
	background: #e6f4ff;
	border-color: #91caff;
}
:global(.o-toggle-list-icon) {
	width: 36px; height: 36px; border-radius: 8px;
	display: inline-flex; align-items: center; justify-content: center;
	background: rgba(0, 0, 0, 0.04);
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
	flex-shrink: 0;
}
:global(.o-toggle-list-icon :global(svg)) { width: 18px; height: 18px; }
:global(.o-toggle-list-icon-on) {
	background: #1677ff;
	color: #fff;
}
:global(.o-toggle-list-body) { flex: 1; min-width: 0; }
:global(.o-toggle-list-title) {
	font-size: 14px; font-weight: 500;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
:global(.o-toggle-list-hint) {
	margin: 4px 0 0;
	font-size: 12px;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}
@media (max-width: 720px) {
	:global(.o-toggle-grid) { grid-template-columns: 1fr; }
}

/* ========== 共享：安装进度 ========== */
:global(.o-progress-wrap) {
	width: 100%;
	max-width: 640px;
	margin: 0 auto;
	display: flex;
	flex-direction: column;
	gap: 8px;
}
:global(.o-progress-rail) {
	width: 100%;
	height: 8px;
	border-radius: 100px;
	background: var(--antd-color-bg-spot, #fafafa);
	overflow: hidden;
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
}
:global(.o-progress-fill) {
	height: 100%;
	background: linear-gradient(90deg, #1677ff 0%, #4096ff 100%);
	border-radius: 100px;
	transition: width 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}
:global(.o-progress-meta) {
	display: flex; align-items: center; justify-content: space-between;
	font-size: 13px;
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
:global(.o-progress-meta strong) {
	color: #1677ff;
	font-weight: 600;
	font-size: 14px;
}

:global(.o-progress) { display: flex; align-items: center; gap: 12px; }
:global(.o-progress-track) {
	flex: 1; height: 8px; border-radius: 100px;
	background: var(--antd-color-bg-spot, #fafafa); overflow: hidden;
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
}
:global(.o-progress-bar) {
	height: 100%;
	background: #1677ff;
	border-radius: 100px;
	transition: width 0.25s ease;
}
:global(.o-progress-label) { font-size: 12px; font-weight: 500; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65)); min-width: 44px; text-align: right; }

/* ========== 共享：安装步骤列表 ========== */
:global(.o-install-steps) {
	list-style: none; padding: 0; margin: 0 auto;
	width: 100%;
	max-width: 520px;
	display: flex; flex-direction: column; gap: 8px;
}
:global(.o-install-step) {
	display: flex; align-items: center; gap: 12px;
	padding: 10px 16px;
	border-radius: 6px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
}
:global(.o-install-step-done) {
	background: #f6ffed;
	border-color: #b7eb8f;
}
:global(.o-install-step-active) {
	background: #e6f4ff;
	border-color: #91caff;
}
:global(.o-install-step-error) {
	background: #fff2f0;
	border-color: #ffccc7;
}
:global(.o-install-mark) {
	width: 20px; height: 20px; flex-shrink: 0;
	display: inline-flex; align-items: center; justify-content: center;
	color: var(--antd-color-text-quaternary, rgba(0, 0, 0, 0.25));
}
:global(.o-install-mark :global(svg)) { width: 20px; height: 20px; }
:global(.o-install-step-done .o-install-mark) { color: #52c41a; }
:global(.o-install-step-active .o-install-mark) { color: #1677ff; }
:global(.o-install-step-error .o-install-mark) { color: #ff4d4f; }
:global(.o-install-name) {
	flex: 1;
	font-size: 14px;
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
:global(.o-install-step-done .o-install-name) { color: var(--antd-color-text, rgba(0, 0, 0, 0.88)); font-weight: 500; }
:global(.o-install-step-active .o-install-name) { color: #1677ff; font-weight: 500; }
:global(.o-install-step-error .o-install-name) { color: #ff4d4f; font-weight: 500; }
:global(.o-install-dot) {
	width: 8px; height: 8px; border-radius: 50%;
	background: var(--antd-color-border, #d9d9d9);
}
:global(.o-spinner) {
	width: 16px; height: 16px;
	border-radius: 50%;
	border: 2px solid #1677ff;
	border-top-color: transparent;
	animation: o-spin-anim 0.8s linear infinite;
}
:global(.o-spinner-mini) {
	width: 12px; height: 12px;
	border-radius: 50%;
	border: 2px solid #1677ff;
	border-top-color: transparent;
	animation: o-spin-anim 0.8s linear infinite;
}

/* ========== 共享：安装成功页 ========== */
:global(.o-success) {
	display: flex; flex-direction: column; align-items: center;
	gap: 20px;
	padding: 24px 0;
}
:global(.o-success-badge) {
	width: 80px; height: 80px; border-radius: 50%;
	background: #f6ffed;
	border: 3px solid #52c41a;
	display: inline-flex; align-items: center; justify-content: center;
	color: #52c41a;
}
:global(.o-success-badge :global(svg)) { width: 44px; height: 44px; }
:global(.o-confetti) {
	color: #faad14;
}
:global(.o-confetti :global(svg)) { width: 32px; height: 32px; }
:global(.o-success-card) {
	width: 100%;
	max-width: 520px;
	padding: 20px 24px;
	border-radius: 8px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	display: flex;
	flex-direction: column;
	gap: 12px;
}
:global(.o-success-row) {
	display: flex; align-items: center; justify-content: space-between;
	gap: 16px;
	padding: 10px 0;
	border-bottom: 1px dashed var(--antd-color-border-light, #f0f0f0);
}
:global(.o-success-row:last-child) {
	border-bottom: none;
	padding-bottom: 0;
}
:global(.o-success-row:first-child) {
	padding-top: 0;
}
:global(.o-success-label) {
	display: inline-flex; align-items: center; gap: 6px;
	font-size: 14px;
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
:global(.o-success-label :global(svg)) { width: 14px; height: 14px; color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45)); }
:global(.o-success-value) {
	font-size: 14px;
	font-weight: 600;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	word-break: break-all;
	text-align: right;
}
:global(.o-success-link) {
	color: #1677ff;
}
:global(.o-success-actions) {
	display: inline-flex; align-items: center; gap: 12px; flex-wrap: wrap;
}

/* ========== 共享：数据库选择卡片 ========== */
:global(.o-db-select) {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16px;
}
:global(.o-db-card) {
	position: relative;
	display: flex; align-items: flex-start; gap: 16px;
	padding: 20px;
	border-radius: 8px;
	background: var(--antd-color-bg-surface, #fff);
	border: 1px solid var(--antd-color-border, #d9d9d9);
	cursor: pointer;
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
:global(.o-db-card:hover) {
	border-color: #4096ff;
}
:global(.o-db-card input[type="radio"]) {
	position: absolute;
	opacity: 0;
	pointer-events: none;
}
:global(.o-db-card-active) {
	background: #e6f4ff;
	border-color: #1677ff;
	box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.1);
}
:global(.o-db-visual) {
	width: 48px; height: 48px; border-radius: 8px;
	display: inline-flex; align-items: center; justify-content: center;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
	flex-shrink: 0;
}
:global(.o-db-visual :global(svg)) { width: 24px; height: 24px; }
:global(.o-db-card-active .o-db-visual-sqlite) {
	background: #e6f4ff;
	border-color: #91caff;
	color: #1677ff;
}
:global(.o-db-card-active .o-db-visual-pg) {
	background: #f9f0ff;
	border-color: #d3adf7;
	color: #722ed1;
}
:global(.o-db-body) { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
:global(.o-db-head) {
	display: flex; align-items: center; justify-content: space-between;
	gap: 8px; flex-wrap: wrap;
}
:global(.o-db-title) {
	margin: 0;
	font-size: 16px; font-weight: 600;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
:global(.o-tag) {
	display: inline-flex; align-items: center; gap: 4px;
	padding: 0 7px;
	height: 22px;
	border-radius: 4px;
	font-size: 12px; font-weight: 500;
}
:global(.o-tag :global(svg)) { width: 12px; height: 12px; }
:global(.o-tag-recommended) {
	background: #f6ffed;
	color: #389e0d;
	border: 1px solid #b7eb8f;
}
:global(.o-db-desc) {
	margin: 0;
	font-size: 13px;
	line-height: 1.6;
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
:global(.o-db-pros) {
	list-style: none; padding: 0; margin: 0;
	display: flex; flex-direction: column; gap: 6px;
}
:global(.o-db-pros li) {
	display: inline-flex; align-items: center; gap: 6px;
	font-size: 12px;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}
:global(.o-db-pros :global(svg)) { width: 14px; height: 14px; color: #52c41a; }
@media (max-width: 720px) {
	:global(.o-db-select) { grid-template-columns: 1fr; }
}

/* ========== 暗色模式覆盖 ========== */
:global(html.dark) {
	--antd-color-bg-body: #0a0a0a;
	--antd-color-bg-surface: #141414;
	--antd-color-bg-elevated: #1d1d1d;
	--antd-color-bg-spot: #161616;
	--antd-color-text: rgba(255, 255, 255, 0.88);
	--antd-color-text-secondary: rgba(255, 255, 255, 0.65);
	--antd-color-text-tertiary: rgba(255, 255, 255, 0.45);
	--antd-color-text-quaternary: rgba(255, 255, 255, 0.25);
	--antd-color-border: #424242;
	--antd-color-border-light: #303030;
	--antd-color-split: #303030;
}
:global(html.dark .o-btn-default),
:global(html.dark .o-field input) {
	background: var(--antd-color-bg-surface, #141414);
	color: var(--antd-color-text, rgba(255, 255, 255, 0.88));
}
:global(html.dark .o-btn-default:hover:not(:disabled)) {
	background: #1f1f1f;
	color: #4096ff;
	border-color: #4096ff;
}
:global(html.dark .o-pop-item:hover) {
	background: rgba(255, 255, 255, 0.09);
}
:global(html.dark .o-toggle-list:hover) {
	border-color: #4096ff;
}
:global(html.dark .o-form-card),
:global(html.dark .o-success-card),
:global(html.dark .o-progress-rail),
:global(html.dark .o-progress-track),
:global(html.dark .o-install-step),
:global(html.dark .o-toggle-list),
:global(html.dark .o-db-card),
:global(html.dark .o-offline-details) {
	background: var(--antd-color-bg-spot, #161616);
}
:global(html.dark .o-inline-code) {
	background: #1a1a1a;
	color: #ffa940;
}
</style>
