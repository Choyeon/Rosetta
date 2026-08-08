<script lang="ts">
import Icon from "@/components/common/Icon.svelte";
import { WELCOME_FEATURES } from "@/composables/oobe/useOobeWizard.svelte";
import { createEventDispatcher } from "svelte";

export let installing: boolean = false;
const dispatch = createEventDispatcher<{ quick: void }>();
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

		<!-- 一键 OOBE 入口：位于第一步欢迎区的突出位置 -->
		<div class="o-quick-wrap" role="region" aria-label="一键安装">
			<div class="o-quick-card">
				<div class="o-quick-left">
					<div class="o-quick-icon" aria-hidden="true">
						<Icon icon="material-symbols:rocket-launch-rounded" />
					</div>
					<div class="o-quick-body">
						<div class="o-quick-title">一键 OOBE · 快速启动</div>
						<p class="o-quick-sub">
							使用预配置的站点信息与管理员账户（Choyeon · choyeon@foxmail.com），配合 30+ 篇四语言示例文章，一步完成安装与种子数据写入。
						</p>
						<ul class="o-quick-meta">
							<li>
								<Icon icon="material-symbols:person-outline-rounded" />
								管理员：Choyeon
							</li>
							<li>
								<Icon icon="material-symbols:alternate-email-rounded" />
								Email：choyeon@foxmail.com
							</li>
							<li>
								<Icon icon="material-symbols:language-outline-rounded" />
								站点：rosetta.choyeon.cc
							</li>
							<li>
								<Icon icon="material-symbols:auto-awesome-rounded" />
								含 30+ 篇四语言文章与真实评论
							</li>
						</ul>
					</div>
				</div>
				<div class="o-quick-right">
					<button
						type="button"
						class="o-btn-quick"
						disabled={installing}
						on:click={() => dispatch("quick")}
						title="一键完成安装并写入示例数据"
					>
						{#if installing}
							<Icon icon="material-symbols:progress-activity-rounded" class="o-spin" />
							安装中…
						{:else}
							<Icon icon="material-symbols:flash-on-rounded" />
							一键 OOBE
						{/if}
					</button>
					<div class="o-quick-hint">
						<Icon icon="material-symbols:info-outline-rounded" />
						若需自定义数据库、Redis 或开关项，点击右下角「开始安装」走分步向导。
					</div>
				</div>
			</div>
		</div>
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
.o-welcome-hero { display: flex; flex-direction: column; gap: 20px; }
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

/* ========== 一键 OOBE 卡片 ========== */
.o-quick-wrap { margin-top: 4px; }
.o-quick-card {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: 20px;
	padding: 18px 20px;
	border-radius: 10px;
	background: linear-gradient(135deg, rgba(22, 119, 255, 0.08) 0%, rgba(114, 46, 209, 0.06) 100%);
	border: 1px solid rgba(22, 119, 255, 0.28);
	box-shadow: 0 2px 10px 0 rgba(22, 119, 255, 0.06);
}
:global(html.dark) .o-quick-card {
	background: linear-gradient(135deg, rgba(22, 119, 255, 0.14) 0%, rgba(114, 46, 209, 0.10) 100%);
	border-color: rgba(22, 119, 255, 0.35);
}
.o-quick-left {
	display: flex; align-items: flex-start; gap: 14px;
	min-width: 0;
}
.o-quick-icon {
	flex-shrink: 0;
	width: 44px; height: 44px;
	display: inline-flex; align-items: center; justify-content: center;
	border-radius: 10px;
	background: linear-gradient(135deg, #1677ff 0%, #722ed1 100%);
	color: #fff;
	box-shadow: 0 4px 12px 0 rgba(22, 119, 255, 0.28);
}
.o-quick-icon :global(svg) { width: 22px; height: 22px; }
.o-quick-body {
	display: flex; flex-direction: column; gap: 8px; min-width: 0;
}
.o-quick-title {
	font-size: 16px; font-weight: 600; line-height: 1.4;
	color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
}
.o-quick-sub {
	margin: 0;
	font-size: 13px; line-height: 1.65;
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
.o-quick-meta {
	list-style: none; padding: 0; margin: 2px 0 0;
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 6px 14px;
}
.o-quick-meta li {
	display: inline-flex; align-items: center; gap: 6px;
	font-size: 12.5px; line-height: 1.5;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
	white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.o-quick-meta :global(svg) { width: 14px; height: 14px; flex-shrink: 0; color: #1677ff; }

.o-quick-right {
	display: flex; flex-direction: column; align-items: flex-end; gap: 8px;
	justify-content: center;
}
.o-btn-quick {
	display: inline-flex; align-items: center; justify-content: center; gap: 6px;
	height: 40px;
	padding: 0 18px;
	border-radius: 8px;
	border: 1px solid transparent;
	font-size: 14.5px; font-weight: 600; line-height: 1.2;
	cursor: pointer;
	font-family: inherit;
	white-space: nowrap;
	color: #fff;
	background: linear-gradient(135deg, #1677ff 0%, #722ed1 100%);
	box-shadow: 0 4px 14px 0 rgba(22, 119, 255, 0.28);
	transition: all 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
.o-btn-quick:hover:not(:disabled) {
	transform: translateY(-1px);
	box-shadow: 0 6px 20px 0 rgba(22, 119, 255, 0.36);
	filter: brightness(1.05);
}
.o-btn-quick:active:not(:disabled) { transform: translateY(0); filter: brightness(0.97); }
.o-btn-quick:disabled { opacity: 0.65; cursor: not-allowed; }
.o-btn-quick :global(svg) { width: 18px; height: 18px; flex-shrink: 0; }

.o-spin {
	animation: o-spin-anim 1s linear infinite;
}
@keyframes o-spin-anim {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}

.o-quick-hint {
	display: inline-flex; align-items: center; gap: 4px;
	max-width: 260px;
	font-size: 12px; line-height: 1.5;
	color: var(--antd-color-text-quaternary, rgba(0, 0, 0, 0.45));
	text-align: right;
}
.o-quick-hint :global(svg) { width: 13px; height: 13px; flex-shrink: 0; }

@media (max-width: 860px) {
	.o-quick-card {
		grid-template-columns: 1fr;
		gap: 14px;
	}
	.o-quick-right { align-items: stretch; }
	.o-btn-quick { width: 100%; }
	.o-quick-hint { max-width: none; text-align: left; }
	.o-quick-meta { grid-template-columns: 1fr; }
}

/* ========== 特性网格 ========== */
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
