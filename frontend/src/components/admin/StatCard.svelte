<script lang="ts">
import Sparkline from "./Sparkline.svelte";

type Props = {
	title: string;
	value: string | number;
	change?: number; // e.g. 0.12 = +12%
	iconSvg?: string; // SVG inner content
	colorName?: "primary" | "secondary" | "success" | "accent";
	sparkData?: number[];
};
let props: Props = $props();

const COLOR_MAP = {
	primary: "var(--ochre-500)",
	secondary: "var(--indigo-500)",
	success: "var(--sage-500)",
	accent: "var(--walnut-500)",
};
const cardColor = $derived(COLOR_MAP[props.colorName ?? "primary"]);
const deltaLabel = $derived.by(() => {
	if (props.change == null || Number.isNaN(props.change)) return null;
	const pct = (props.change * 100).toFixed(1).replace(/\.0$/, "");
	const sign = props.change >= 0 ? "+" : "";
	return `${sign}${pct}%`;
});
const deltaPositive = $derived(props.change == null ? true : props.change >= 0);
</script>

<div class="stat-card" style="--card-accent: {cardColor};">
	<div class="stat-head">
		{#if props.iconSvg}
			<div class="stat-icon">{@html props.iconSvg}</div>
		{/if}
		<div class="stat-label">{props.title}</div>
		{#if deltaLabel != null}
			<span class="stat-delta" class:up={deltaPositive} class:down={!deltaPositive}>{deltaLabel}</span>
		{/if}
	</div>
	<div class="stat-value">{props.value}</div>
	{#if props.sparkData && props.sparkData.length > 0}
		<div class="stat-spark">
			<Sparkline data={props.sparkData} color={cardColor} width={140} height={36} />
		</div>
	{/if}
</div>

<style>
	.stat-card {
		background: hsl(var(--b1));
		border: 1px solid hsl(var(--b3));
		border-radius: 14px;
		padding: 16px 18px;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03), 0 8px 24px -16px rgba(0, 0, 0, 0.15);
		display: flex;
		flex-direction: column;
		gap: 8px;
		position: relative;
		overflow: hidden;
		transition: transform 180ms ease, box-shadow 180ms ease;
	}
	.stat-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04), 0 14px 32px -18px rgba(0, 0, 0, 0.22);
	}
	.stat-card::before {
		content: '';
		position: absolute;
		top: 0; left: 0;
		width: 4px; height: 100%;
		background: var(--card-accent, var(--ochre-500));
		opacity: 0.9;
	}
	.stat-head {
		display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
	}
	.stat-icon {
		width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center;
		color: var(--card-accent, var(--ochre-500));
		background: color-mix(in srgb, var(--card-accent, var(--ochre-500)) 14%, transparent);
		border-radius: 8px;
	}
	.stat-icon :global(svg) { width: 16px; height: 16px; }
	.stat-label {
		font-size: 12px; font-weight: 600;
		color: hsl(var(--bc) / 0.65);
		letter-spacing: 0.02em;
	}
	.stat-delta {
		margin-left: auto;
		font-size: 11.5px; font-weight: 800;
		padding: 2px 8px; border-radius: 999px;
	}
	.stat-delta.up {
		color: hsl(148, 70%, 30%);
		background: color-mix(in srgb, hsl(148, 70%, 46%) 18%, transparent);
	}
	.stat-delta.down {
		color: hsl(0, 70%, 40%);
		background: color-mix(in srgb, hsl(0, 80%, 58%) 18%, transparent);
	}
	.stat-value {
		font-size: 28px; font-weight: 900; letter-spacing: -0.02em;
		color: hsl(var(--bc));
		line-height: 1.1;
	}
	.stat-spark {
		margin-top: 4px;
	}
</style>
