<script lang="ts">
import Icon from "@/components/common/Icon.svelte";
import { oobe } from "@/composables/oobe/useOobeWizard.svelte";
</script>

<div class="o-step-inner">
	<header class="o-step-head">
		<div class="o-step-tag">
			<Icon icon="material-symbols:health-metrics-outline-rounded" />
			Environment Check
		</div>
		<h2 class="o-h2">运行环境检测</h2>
		<p class="o-lead">自动检查部署所需的基础环境，任何项未通过也可继续安装。若依赖缺失，可点击下方的"安装运行依赖"。</p>
	</header>

	{#if oobe.envLoading}
		<ul class="o-skeleton-grid" aria-hidden="true">
			{#each Array(8) as _, i}
				<li class="o-skeleton" style={`animation-delay: ${i * 55}ms`}></li>
			{/each}
		</ul>
	{:else}
		<ul class="o-env-grid">
			{#each oobe.envChecks as item, idx}
				<li class="o-env-card" class:o-env-pass={item.status === "pass"} class:o-env-fail={item.status === "fail"}>
					<div
						class="o-env-icon"
						class:o-env-icon-pass={item.status === "pass"}
						class:o-env-icon-fail={item.status === "fail"}
						class:o-env-icon-info={item.status === "info"}
						aria-hidden="true"
					>
						<Icon
							icon={
								item.status === "pass"
									? "material-symbols:check-circle-rounded"
									: item.status === "fail"
									? "material-symbols:cancel-rounded"
									: "material-symbols:info-rounded"
							}
						/>
					</div>
					<div class="o-env-main">
						<div class="o-env-top">
							<span class="o-env-name">
								<Icon icon="material-symbols:checklist-rounded" class="o-list-bullet" />
								{item.name}
							</span>
							<span
								class="o-env-badge"
								class:o-env-badge-pass={item.status === "pass"}
								class:o-env-badge-fail={item.status === "fail"}
								class:o-env-badge-info={item.status === "info"}
							>
								{item.value}
							</span>
						</div>
						{#if item.detail}
							<div class="o-env-detail-wrap">
								<button
									type="button"
									class="o-expand-link"
									on:click={() => (oobe.showErrorDetail[idx] = !oobe.showErrorDetail[idx])}
									aria-expanded={!!oobe.showErrorDetail[idx]}
								>
									{oobe.showErrorDetail[idx] ? "收起详情" : "查看详情"}
									<Icon icon={oobe.showErrorDetail[idx] ? "material-symbols:expand-less-rounded" : "material-symbols:expand-more-rounded"} />
								</button>
								{#if oobe.showErrorDetail[idx]}
									<div class="o-env-detail">
										<Icon icon="material-symbols:info-outline-rounded" />
										<p>{item.detail}</p>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				</li>
			{/each}
		</ul>

		{#if oobe.envChecks.some((c) => c.status === "fail")}
			<div class="o-callout o-callout-warn" role="alert">
				<Icon icon="material-symbols:warning-rounded" />
				<div class="o-callout-body">
					<strong>部分检测项未通过</strong>
					<p>您仍可继续安装，但部分功能可能受限。建议检查相关依赖后重试。</p>
				</div>
			</div>
		{/if}

		<!-- ===== 依赖列表 + 一键安装（新功能） ===== -->
		<section class="o-dep-section" aria-label="运行依赖">
			<header class="o-dep-head">
				<div class="o-step-tag o-step-tag-soft">
					<Icon icon="material-symbols:deployed-code-outline-rounded" />
					Dependencies
				</div>
				<div class="o-dep-actions">
					<button
						type="button"
						class="o-btn o-btn-default o-btn-sm"
						on:click={() => oobe.loadDeps(true)}
						disabled={oobe.depsLoading || oobe.depsInstalling}
					>
						<Icon icon="material-symbols:refresh-rounded" />
						{oobe.depsLoading ? "读取中…" : "重新扫描"}
					</button>
					<button
						type="button"
						class="o-btn o-btn-primary o-btn-sm"
						on:click={() => oobe.installDeps()}
						disabled={oobe.depsInstalling || oobe.depsLoading}
					>
						<Icon icon={oobe.depsInstalling ? "material-symbols:sync-rounded" : "material-symbols:download-rounded"} />
						{oobe.depsInstalling ? `安装中 ${oobe.depsInstallProgress}%` : "安装运行依赖"}
					</button>
				</div>
			</header>

			{#if oobe.depsLoading && oobe.deps.length === 0}
				<ul class="o-skeleton-grid" aria-hidden="true">
					{#each Array(4) as _, i}
						<li class="o-skeleton" style={`animation-delay: ${i * 50}ms`}></li>
					{/each}
				</ul>
			{:else if oobe.deps.length > 0}
				<ul class="o-dep-list">
					{#each oobe.deps as d}
						<li
							class="o-dep-row"
							class:o-dep-row--installed={d.installed}
							class:o-dep-row--missing={!d.installed && d.required}
						>
							<div class="o-dep-icon" aria-hidden="true">
								<Icon
									icon={
										d.installed
											? "material-symbols:check-circle-outline-rounded"
											: d.required
											  ? "material-symbols:error-outline-rounded"
											  : "material-symbols:info-outline-rounded"
									}
								/>
							</div>
							<div class="o-dep-body">
								<div class="o-dep-top">
									<span class="o-dep-name">{d.label || d.name}</span>
									<span
										class="o-dep-badge"
										class:o-dep-badge--ok={d.installed}
										class:o-dep-badge--bad={!d.installed && d.required}
									>
										{d.installed ? (d.version || "已安装") : d.required ? "缺少" : "可选"}
									</span>
								</div>
								{#if d.required_version || d.detail}
									<div class="o-dep-sub">
										{#if d.required_version}
											<span class="o-dep-chip">要求：{d.required_version}</span>
										{/if}
										{#if d.detail}
											<span class="o-dep-note">{d.detail}</span>
										{/if}
									</div>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<div class="o-empty">
					<Icon icon="material-symbols:inbox-rounded" />
					<p>暂无依赖数据，点击"重新扫描"或直接安装运行依赖。</p>
				</div>
			{/if}

			{#if oobe.depsInstalling}
				<div class="o-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={oobe.depsInstallProgress}>
					<div class="o-progress-track">
						<div class="o-progress-bar" style={`width:${oobe.depsInstallProgress}%`}></div>
					</div>
					<div class="o-progress-label">{oobe.depsInstallProgress}%</div>
				</div>
			{/if}

			{#if (oobe.depsInstallLog.length > 0 && oobe.depsInstalling) || oobe.depsInstallError}
				<details class="o-logbox" open={!!oobe.depsInstalling}>
					<summary>安装日志 {oobe.depsInstallError ? `（失败：${oobe.depsInstallError}）` : ""}</summary>
					<pre class="o-logbox-pre" id="oobe-dep-log">{#each oobe.depsInstallLog as L}{L + "\n"}{/each}{#if oobe.depsInstallError}{"✖ " + oobe.depsInstallError}{/if}</pre>
				</details>
			{/if}
		</section>
	{/if}
</div>

<style>
/* ===== Skeleton ===== */
.o-skeleton-grid {
	list-style: none; padding: 0; margin: 0;
	display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;
}
@media (max-width: 640px) { .o-skeleton-grid { grid-template-columns: 1fr; } }
.o-skeleton {
	height: 72px; border-radius: 8px;
	background: linear-gradient(90deg, var(--antd-color-bg-surface, #fff) 25%, var(--antd-color-bg-spot, #fafafa) 37%, var(--antd-color-bg-surface, #fff) 63%);
	background-size: 400% 100%;
	animation: o-skeleton 1.2s ease-in-out infinite both;
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
}
@keyframes o-skeleton {
	0% { background-position: 100% 50%; }
	100% { background-position: 0 50%; }
}

/* ===== Env Grid ===== */
.o-env-grid {
	list-style: none; padding: 0; margin: 0;
	display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;
}
@media (max-width: 760px) { .o-env-grid { grid-template-columns: 1fr; } }

.o-env-card {
	display: flex; align-items: flex-start; gap: 12px;
	padding: 16px;
	border-radius: 8px;
	background: var(--antd-color-bg-surface, #fff);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
	transition: border-color 0.2s cubic-bezier(0.645, 0.045, 0.355, 1), box-shadow 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
:global(html.dark) .o-env-card {
	background: var(--antd-color-bg-surface, #141414);
	border-color: var(--antd-color-border-light, #303030);
}
.o-env-pass { border-color: #b7eb8f; }
.o-env-fail { border-color: #ffa39e; }

.o-env-icon {
	flex-shrink: 0;
	width: 32px; height: 32px; border-radius: 8px;
	display: inline-flex; align-items: center; justify-content: center;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}
.o-env-icon :global(svg) { width: 16px; height: 16px; }
.o-env-icon-pass {
	background: #f6ffed;
	border-color: #b7eb8f;
	color: #52c41a;
}
.o-env-icon-fail {
	background: #fff2f0;
	border-color: #ffccc7;
	color: #ff4d4f;
}
.o-env-icon-info {
	background: #e6f4ff;
	border-color: #91caff;
	color: #1677ff;
}

.o-env-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.o-env-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.o-env-name {
	display: inline-flex; align-items: center; gap: 6px;
	font-size: 14px; font-weight: 500; color: var(--antd-color-text, rgba(0, 0, 0, 0.88));
	min-width: 0;
}
.o-list-bullet { width: 14px; height: 14px; flex-shrink: 0; color: #1677ff; }

.o-env-badge {
	display: inline-flex; align-items: center; justify-content: center;
	padding: 0 7px;
	height: 22px;
	border-radius: 4px;
	font-size: 12px; font-weight: 500; line-height: 22px;
	background: var(--antd-color-bg-spot, #fafafa);
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	flex-shrink: 0;
}
.o-env-badge-pass {
	background: #f6ffed;
	color: #389e0d;
	border-color: #b7eb8f;
}
.o-env-badge-fail {
	background: #fff2f0;
	color: #cf1322;
	border-color: #ffa39e;
}
.o-env-badge-info {
	background: #e6f4ff;
	color: #0958d9;
	border-color: #91caff;
}

.o-env-detail-wrap { display: flex; flex-direction: column; gap: 8px; }
.o-expand-link {
	display: inline-flex; align-items: center; gap: 4px; align-self: flex-start;
	padding: 0 6px; height: 24px; margin: 0 -6px; border-radius: 4px;
	background: transparent; border: none; cursor: pointer;
	font-size: 12px; font-weight: 500; color: #1677ff;
	font-family: inherit;
	transition: color 0.2s cubic-bezier(0.645, 0.045, 0.355, 1);
}
.o-expand-link:hover { background: #e6f4ff; color: #4096ff; }
.o-expand-link :global(svg) { width: 14px; height: 14px; }
.o-env-detail {
	display: flex; gap: 8px; padding: 10px 12px;
	border-radius: 6px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
}
:global(html.dark) .o-env-detail {
	background: var(--antd-color-bg-spot, #161616);
}
.o-env-detail :global(svg) { width: 14px; height: 14px; flex-shrink: 0; margin-top: 2px; color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45)); }
.o-env-detail p { margin: 0; font-size: 12.5px; line-height: 1.6; color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65)); }

/* ===== Dependencies section ===== */
.o-dep-section {
	display: flex; flex-direction: column; gap: 12px;
	padding: 20px;
	border-radius: 8px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
}
:global(html.dark) .o-dep-section {
	background: var(--antd-color-bg-spot, #161616);
	border-color: var(--antd-color-border-light, #303030);
}
.o-dep-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.o-dep-actions { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.o-dep-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.o-dep-row {
	display: flex; align-items: flex-start; gap: 12px;
	padding: 12px 16px; border-radius: 6px;
	background: var(--antd-color-bg-surface, #fff);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
}
:global(html.dark) .o-dep-row { background: var(--antd-color-bg-surface, #141414); border-color: var(--antd-color-border-light, #303030); }
.o-dep-row--installed { border-color: #b7eb8f; background: #f6ffed; }
:global(html.dark) .o-dep-row--installed { background: rgba(82, 196, 26, 0.08); }
.o-dep-row--missing { border-color: #ffa39e; background: #fff2f0; }
:global(html.dark) .o-dep-row--missing { background: rgba(255, 77, 79, 0.08); }

.o-dep-icon {
	flex-shrink: 0; width: 28px; height: 28px; border-radius: 6px;
	display: inline-flex; align-items: center; justify-content: center;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}
.o-dep-icon :global(svg) { width: 14px; height: 14px; }
.o-dep-row--installed .o-dep-icon {
	background: #f6ffed;
	color: #52c41a;
	border-color: #b7eb8f;
}
.o-dep-row--missing .o-dep-icon {
	background: #fff2f0;
	color: #ff4d4f;
	border-color: #ffa39e;
}

.o-dep-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.o-dep-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.o-dep-name { font-size: 14px; font-weight: 500; color: var(--antd-color-text, rgba(0, 0, 0, 0.88)); min-width: 0; }
.o-dep-badge {
	display: inline-flex; align-items: center; justify-content: center;
	padding: 0 7px;
	height: 20px;
	border-radius: 4px;
	font-size: 11.5px; font-weight: 500; line-height: 20px;
	background: var(--antd-color-bg-spot, #fafafa);
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	flex-shrink: 0;
}
.o-dep-badge--ok {
	background: #f6ffed;
	color: #389e0d;
	border-color: #b7eb8f;
}
.o-dep-badge--bad {
	background: #fff2f0;
	color: #cf1322;
	border-color: #ffa39e;
}

.o-dep-sub { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.o-dep-chip {
	display: inline-flex; align-items: center;
	padding: 0 7px;
	height: 20px;
	border-radius: 4px;
	font-size: 11.5px; font-weight: 500; line-height: 20px;
	background: var(--antd-color-bg-spot, #fafafa);
	border: 1px solid var(--antd-color-border-light, #f0f0f0);
	color: var(--antd-color-text-secondary, rgba(0, 0, 0, 0.65));
}
.o-dep-note { font-size: 12px; color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45)); }

.o-empty {
	display: flex; flex-direction: column; align-items: center; justify-content: center;
	gap: 8px; padding: 24px 10px;
	border-radius: 8px;
	color: var(--antd-color-text-tertiary, rgba(0, 0, 0, 0.45));
}
.o-empty :global(svg) { width: 28px; height: 28px; }
.o-empty p { margin: 0; font-size: 13px; }

.o-logbox {
	margin: 0;
	border-radius: 6px;
	background: #1f1f1f;
	color: #e8e8e8;
	border: 1px solid #333;
	overflow: hidden;
}
.o-logbox summary {
	cursor: pointer;
	padding: 10px 14px;
	font-size: 12.5px; font-weight: 500;
	color: #e8e8e8;
	list-style: none;
	border-bottom: 1px solid #333;
}
.o-logbox summary::-webkit-details-marker { display: none; }
.o-logbox pre {
	margin: 0; padding: 12px 14px;
	max-height: 200px; overflow: auto;
	font-size: 11.5px; line-height: 1.55;
	font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
	white-space: pre-wrap; word-break: break-word;
}
</style>
