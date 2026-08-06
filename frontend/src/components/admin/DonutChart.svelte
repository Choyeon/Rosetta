<script lang="ts">
type Props = {
	data: { label: string; value: number; color?: string }[];
	size?: number;
	thickness?: number;
	showLegend?: boolean;
	centerLabel?: string;
	centerValue?: string | number;
	title?: string;
	width?: string | number;
};
let props: Props = $props();
const PALETTE = [
	"var(--ochre-500)",
	"var(--indigo-500)",
	"var(--sage-500)",
	"var(--walnut-500)",
	"var(--ochre-300)",
	"var(--indigo-300)",
	"var(--sage-300)",
	"var(--walnut-300)",
];
function formatNum(v: number): string {
	const abs = Math.abs(v);
	if (abs >= 1e9) return `${(v / 1e9).toFixed(1).replace(/\.0$/, "")}B`;
	if (abs >= 1e6) return `${(v / 1e6).toFixed(1).replace(/\.0$/, "")}M`;
	if (abs >= 1e3) return `${(v / 1e3).toFixed(1).replace(/\.0$/, "")}K`;
	return String(Number(v.toFixed(2)));
}
const p = $derived({
	size: 220,
	thickness: 28,
	showLegend: true,
	width: "100%",
	...props,
});
const styleWidth = $derived(
	typeof p.width === "number" ? `${p.width}px` : p.width,
);
const c = $derived.by(() => {
	const total = p.data.reduce((s, d) => s + Math.max(0, d.value), 0) || 1;
	const cx = p.size / 2;
	const cy = p.size / 2;
	const R = p.size / 2 - 4;
	const r = R - p.thickness;
	let acc = -Math.PI / 2;
	const segments = p.data.map((d, i) => {
		const v = Math.max(0, d.value);
		const angle = (v / total) * Math.PI * 2;
		const start = acc;
		const end = acc + angle;
		acc = end;
		const deg = (angle * 180) / Math.PI;
		const largeArc = deg > 180 ? 1 : 0;
		const sx = cx + R * Math.cos(start);
		const sy = cy + R * Math.sin(start);
		const ex = cx + R * Math.cos(end);
		const ey = cy + R * Math.sin(end);
		const isx = cx + r * Math.cos(end);
		const isy = cy + r * Math.sin(end);
		const ix0 = cx + r * Math.cos(start);
		const iy0 = cy + r * Math.sin(start);
		const color = d.color ?? PALETTE[i % PALETTE.length];
		let pathD = "";
		if (Math.abs(angle - Math.PI * 2) < 1e-6) {
			pathD = `M ${cx} ${cy - R} A ${R} ${R} 0 1 1 ${cx - 0.001} ${cy - R} L ${cx - 0.001} ${cy - r} A ${r} ${r} 0 1 0 ${cx} ${cy - r} Z`;
		} else if (angle >= 1e-6) {
			pathD = `M ${sx} ${sy} A ${R} ${R} 0 ${largeArc} 1 ${ex} ${ey} L ${isx} ${isy} A ${r} ${r} 0 ${largeArc} 0 ${ix0} ${iy0} Z`;
		}
		return { ...d, color, pathD, percent: (v / total) * 100 };
	});
	return { cx, cy, segments, total };
});
</script>

<div style="width:{styleWidth};display:block;">
	{#if p.title}
		<div style="font-size:13px;font-weight:700;color:hsl(var(--bc));margin-bottom:8px;text-align:left;">{p.title}</div>
	{/if}
	{#each [c] as cc}
		<div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
			<svg viewBox="0 0 {p.size} {p.size}" preserveAspectRatio="xMidYMid meet" style="width:{p.size}px;height:{p.size}px;flex-shrink:0;">
				{#each cc.segments as s, i}
					{#if s.pathD}
						<path d={s.pathD} fill={s.color} />
					{/if}
				{/each}
				{#if p.centerLabel}
					<text x={cc.cx} y={cc.cy - 8} text-anchor="middle" font-size="11" fill="hsl(var(--bc) / 0.55)">{p.centerLabel}</text>
				{/if}
				{#if p.centerValue != null}
					<text x={cc.cx} y={cc.cy + 16} text-anchor="middle" dominant-baseline="middle" font-size="28" font-weight="700" fill="var(--ochre-600)">{p.centerValue}</text>
				{/if}
			</svg>
			{#if p.showLegend}
				<div style="display:flex;flex-direction:column;gap:8px;flex:1 1 120px;min-width:0;">
					{#each cc.segments as s, i}
						<div style="display:flex;align-items:center;gap:8px;">
							<span style="width:8px;height:8px;border-radius:50%;background:{s.color};flex-shrink:0;"></span>
							<span style="font-size:12px;color:hsl(var(--bc) / 0.8);flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{s.label}</span>
							<span style="font-size:12px;font-weight:700;color:hsl(var(--bc));flex-shrink:0;">{formatNum(s.value)}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/each}
</div>
