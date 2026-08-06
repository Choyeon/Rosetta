<script lang="ts">
import Icon from "@/components/common/Icon.svelte";
import { WELCOME_FEATURES } from "@/composables/oobe/useOobeWizard.svelte";
</script>

<div class="o-welcome">
	<div class="o-welcome-hero">
		<span class="o-chips">
			<span class="o-chip o-chip-accent">
				<Icon icon="material-symbols:verified-rounded" />
				v6.15 · 稳定版
			</span>
			<span class="o-chip">
				<Icon icon="material-symbols:bolt-rounded" />
				FastAPI + Astro
			</span>
			<span class="o-chip">
				<Icon icon="material-symbols:palette-rounded" />
				多主题 · 可扩展
			</span>
		</span>
		<h2 class="o-h2">
			欢迎使用 <span class="o-brand-name">Rosetta</span>
		</h2>
		<p class="o-lead">
			一个功能齐全、主题优雅、开箱即用的现代博客引擎。内置 Markdown 扩展、评论系统、多语言、SEO 优化与数据面板，让创作回归纯粹。
		</p>
	</div>

	<ul class="o-feature-grid" aria-label="核心特性">
		{#each WELCOME_FEATURES as f, idx}
			<li class="o-feature-card" style={`animation-delay: ${60 * idx}ms`}>
				<div class="o-feature-icon" aria-hidden="true">
					<Icon icon={f.icon} />
				</div>
				<div class="o-feature-body">
					<h3 class="o-feature-title">{f.title}</h3>
					<p class="o-feature-desc">{f.desc}</p>
				</div>
			</li>
		{/each}
	</ul>
</div>

<style>
.o-welcome { display: flex; flex-direction: column; gap: 24px; width: 100%; }
.o-welcome-hero { display: flex; flex-direction: column; gap: 12px; }
.o-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.o-chip {
	display: inline-flex; align-items: center; gap: 6px;
	padding: 0 7px;
	height: 22px;
	border-radius: 4px;
	font-size: 12px; font-weight: 500; line-height: 22px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border, #d9d9d9);
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
:global(html.dark) .o-chip {
	background: var(--antd-color-bg-spot, #161616);
}
.o-chip :global(svg) { width: 12px; height: 12px; }
.o-chip-accent {
	background: #e6f4ff;
	border-color: #91caff;
	color: #1677ff;
}

.o-brand-name { color: #1677ff; }

.o-feature-grid {
	list-style: none; padding: 0; margin: 0;
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 16px;
}
@media (max-width: 900px) { .o-feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .o-feature-grid { grid-template-columns: 1fr; } }

.o-feature-card {
	display: flex; align-items: flex-start; gap: 12px;
	padding: 16px;
	background: var(--antd-color-bg-surface, #ffffff);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	border-radius: 8px;
	animation: o-fade-up 0.3s cubic-bezier(0.215, 0.61, 0.355, 1) both;
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
:global(html.dark) .o-feature-card {
	background: var(--antd-color-bg-surface, #141414);
	border-color: var(--antd-color-border-light, #303030);
}
.o-feature-card:hover {
	border-color: #91caff;
	box-shadow: 0 4px 16px 0 rgba(22, 119, 255, 0.08);
}
@keyframes o-fade-up {
	from { opacity: 0; transform: translateY(6px); }
	to   { opacity: 1; transform: translateY(0); }
}

.o-feature-icon {
	flex-shrink: 0;
	width: 40px; height: 40px;
	display: inline-flex; align-items: center; justify-content: center;
	border-radius: 8px;
	background: #e6f4ff;
	border: 1px solid #91caff;
	color: #1677ff;
}
:global(html.dark) .o-feature-icon {
	background: rgba(22, 119, 255, 0.1);
	border-color: rgba(22, 119, 255, 0.3);
}
.o-feature-icon :global(svg) {
	width: 20px; height: 20px;
}

.o-feature-body { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.o-feature-title {
	margin: 0;
	font-size: 15px; font-weight: 600; line-height: 1.4;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
.o-feature-desc {
	margin: 0;
	font-size: 13px; line-height: 1.6;
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
</style>
