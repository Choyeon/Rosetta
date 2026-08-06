<script lang="ts">
import Icon from "@/components/common/Icon.svelte";
import {
	FEATURE_LABELS,
	FEATURE_META,
	oobe,
} from "@/composables/oobe/useOobeWizard.svelte";
</script>

<div class="o-step-inner">
	<header class="o-step-head">
		<div class="o-step-tag">
			<Icon icon="material-symbols:tune-rounded" />
			Feature Toggles
		</div>
		<h2 class="o-h2">功能开关</h2>
		<p class="o-lead">启用或禁用各项功能。安装完成后可随时在后台设置中调整。</p>
	</header>

	<ul class="o-toggle-grid">
		{#each Object.keys(FEATURE_LABELS) as key}
			{@const on = !!oobe.draft.features[key]}
			{@const meta = FEATURE_META[key] || null}
			<li class="o-toggle-list" class:o-toggle-list-on={on}>
				<div class="o-toggle-list-icon" class:o-toggle-list-icon-on={on} aria-hidden="true">
					{#if meta}<Icon icon={meta.icon} />{/if}
				</div>
				<div class="o-toggle-list-body">
					<div class="o-toggle-list-title">{FEATURE_LABELS[key]}</div>
					<p class="o-toggle-list-hint">{meta?.desc || (on ? "已启用" : "未启用")}</p>
				</div>
				<button
					type="button"
					class="o-switch"
					class:o-switch-on={on}
					role="switch"
					aria-checked={on}
					aria-label={FEATURE_LABELS[key]}
					on:click={() => (oobe.draft.features = { ...oobe.draft.features, [key]: !on })}
				>
					<span class="o-switch-thumb"></span>
				</button>
			</li>
		{/each}
	</ul>
</div>