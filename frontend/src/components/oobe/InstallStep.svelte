<script lang="ts">
import Icon from "@/components/common/Icon.svelte";
import { oobe } from "@/composables/oobe/useOobeWizard.svelte";
</script>

{#if !oobe.installResult}
	<div class="o-installing">
		<header class="o-step-head o-center">
			<div class="o-step-tag o-step-tag-pulse">
				<span class="o-spinner-mini" aria-hidden="true"></span>
				Installing
			</div>
			<h2 class="o-h2 o-center">正在为你准备站点...</h2>
			<p class="o-lead o-center">
				根据你的配置执行初始化，预计 30 秒内完成。请勿关闭页面。
			</p>
		</header>

		<div class="o-progress-wrap">
			<div class="o-progress-rail">
				<div class="o-progress-fill" style={`width: ${oobe.installProgress}%`}></div>
			</div>
			<div class="o-progress-meta">
				<span>安装进度</span>
				<strong>{oobe.installProgress}%</strong>
			</div>
		</div>

		<ol class="o-install-steps">
			{#each oobe.installSteps as item}
				<li
					class="o-install-step"
					class:o-install-step-done={item.status === "done"}
					class:o-install-step-active={item.status === "active"}
					class:o-install-step-error={item.status === "error"}
				>
					<span class="o-install-mark" aria-hidden="true">
						{#if item.status === "done"}
							<Icon icon="material-symbols:check-circle-rounded" />
						{:else if item.status === "error"}
							<Icon icon="material-symbols:error-rounded" />
						{:else if item.status === "active"}
							<span class="o-spinner"></span>
						{:else}
							<span class="o-install-dot"></span>
						{/if}
					</span>
					<span class="o-install-name">{item.name}</span>
				</li>
			{/each}
		</ol>

		{#if oobe.installError}
			<div class="o-callout o-callout-error" role="alert">
				<Icon icon="material-symbols:error-rounded" />
				<div class="o-callout-body">
					<strong>安装失败</strong>
					<p>{oobe.installError}</p>
				</div>
				<button
					class="o-btn o-btn-ghost o-btn-sm"
					type="button"
					on:click={() => {
						try {
							oobe.installError = null;
							void oobe.startInstall();
						} catch (e: any) {
							oobe.showToast("error", e?.message || "重新安装失败");
						}
					}}
					disabled={oobe.installing}
				>
					<Icon icon={oobe.installing ? "material-symbols:sync-rounded" : "material-symbols:refresh-rounded"} />
					{oobe.installing ? "重新安装中…" : "重试"}
				</button>
			</div>
		{:else if !oobe.installing && !oobe.installResult}
			{#if oobe.backendReachable !== "yes"}
				<div class="o-callout o-callout-warn" role="status">
					<Icon icon="material-symbols:cloud-off-outline-rounded" />
					<div class="o-callout-body">
						<strong>后端未连接</strong>
						<p>{oobe.backendLastError || "连接不到后端服务器，无法开始安装"}</p>
					</div>
					<button
						class="o-btn o-btn-primary o-btn-sm"
						type="button"
						on:click={() => { void oobe.checkBackendConnectivity(true); }}
						disabled={oobe.backendCheckLoading}
					>
						<Icon icon={oobe.backendCheckLoading ? "material-symbols:sync-rounded" : "material-symbols:refresh-rounded"} />
						{oobe.backendCheckLoading ? "检查中…" : "重新连接后端"}
					</button>
				</div>
			{/if}
			<button
				class="o-btn o-btn-primary o-btn-block"
				type="button"
				on:click={() => {
					try {
						void oobe.startInstall();
					} catch (e: any) {
						oobe.showToast("error", e?.message || "启动安装失败");
					}
				}}
				disabled={oobe.backendReachable !== "yes" || oobe.installing}
			>
				<Icon icon={oobe.installing ? "material-symbols:sync-rounded" : "material-symbols:play-arrow-rounded"} />
				{oobe.installing ? "安装中…" : "开始安装"}
			</button>
		{/if}
	</div>
{:else}
	<div class="o-success">
		<div class="o-success-badge" aria-hidden="true">
			<Icon icon="material-symbols:workspace-premium-rounded" />
		</div>
		<div class="o-confetti" aria-hidden="true">
			<Icon icon="material-symbols:celebration-rounded" />
		</div>
		<h2 class="o-h2 o-center">安装完成，恭喜你！</h2>
		<p class="o-lead o-center">
			你的 Rosetta 博客已经就绪，开始记录、分享、创造吧。
		</p>

		<div class="o-success-card">
			<div class="o-success-row">
				<span class="o-success-label">
					<Icon icon="material-symbols:label-important-rounded" />
					站点名称
				</span>
				<strong class="o-success-value">{oobe.installResult.siteName}</strong>
			</div>
			<div class="o-success-row">
				<span class="o-success-label">
					<Icon icon="material-symbols:person-outline-rounded" />
					管理员账号
				</span>
				<strong class="o-success-value">{oobe.installResult.adminUsername}</strong>
			</div>
			<div class="o-success-row">
				<span class="o-success-label">
					<Icon icon="material-symbols:link-rounded" />
					首页地址
				</span>
				<strong class="o-success-value o-success-link">{oobe.installResult.frontendUrl}</strong>
			</div>
			<div class="o-success-row">
				<span class="o-success-label">
					<Icon icon="material-symbols:dashboard-customize-rounded" />
					后台地址
				</span>
				<strong class="o-success-value o-success-link">{oobe.installResult.adminUrl}</strong>
			</div>
		</div>

		<div class="o-success-actions">
			<a class="o-btn o-btn-primary" href={oobe.installResult.frontendUrl} target="_self" rel="noreferrer">
				<Icon icon="material-symbols:home-rounded" />
				访问首页
				<Icon icon="material-symbols:arrow-forward-rounded" />
			</a>
			<a class="o-btn o-btn-outline" href={oobe.installResult.adminUrl} target="_self" rel="noreferrer">
				<Icon icon="material-symbols:login-rounded" />
				登录后台
			</a>
		</div>
	</div>
{/if}