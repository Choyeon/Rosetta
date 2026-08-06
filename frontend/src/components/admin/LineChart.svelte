<script lang="ts">
type Props = {
	data: { label: string; value: number }[];
	yTicks?: number;
	area?: boolean;
	smooth?: boolean;
	height?: number;
	showDots?: boolean;
	strokeWidth?: number;
	color?: string;
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

function niceTicks(min: number, max: number, count: number): number[] {
	if (min === max) {
		const v = Math.abs(min) < 1e-9 ? 1 : Math.abs(min);
		return [min - v * 0.5, min, min + v * 0.5];
	}
	const range = max - min;
	const roughStep = range / Math.max(1, count);
	const pow = 10 ** Math.floor(Math.log10(roughStep));
	const norm = roughStep / pow;
	let step: number;
	if (norm <= 1) step = 1;
	else if (norm <= 2) step = 2;
	else if (norm <= 2.5) step = 2.5;
	else if (norm <= 5) step = 5;
	else step = 10;
	step *= pow;
	const start = Math.ceil(min / step) * step;
	const end = Math.floor(max / step) * step;
	const ticks: number[] = [];
	for (let v = start; v <= end + step * 1e-9; v += step)
		ticks.push(Number(v.toFixed(10)));
	if (ticks.length < 2) return [min, max];
	return ticks;
}
function buildLinearPath(points: [number, number][]): string {
	if (points.length === 0) return "";
	let d = `M ${points[0][0]} ${points[0][1]}`;
	for (let i = 1; i < points.length; i++)
		d += ` L ${points[i][0]} ${points[i][1]}`;
	return d;
}
function buildSmoothPath(points: [number, number][]): string {
	if (points.length < 2) return buildLinearPath(points);
	let d = `M ${points[0][0]} ${points[0][1]}`;
	for (let i = 0; i < points.length - 1; i++) {
		const p0 = points[i - 1] ?? points[i];
		const p1 = points[i];
		const p2 = points[i + 1];
		const p3 = points[i + 2] ?? p2;
		const s = 0.2;
		const cp1x = p1[0] + (p2[0] - p0[0]) * s;
		const cp1y = p1[1] + (p2[1] - p0[1]) * s;
		const cp2x = p2[0] - (p3[0] - p1[0]) * s;
		const cp2y = p2[1] - (p3[1] - p1[1]) * s;
		d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2[0]} ${p2[1]}`;
	}
	return d;
}
function formatNum(v: number): string {
	const abs = Math.abs(v);
	if (abs >= 1e9) return `${(v / 1e9).toFixed(1).replace(/\.0$/, "")}B`;
	if (abs >= 1e6) return `${(v / 1e6).toFixed(1).replace(/\.0$/, "")}M`;
	if (abs >= 1e3) return `${(v / 1e3).toFixed(1).replace(/\.0$/, "")}K`;
	return String(Number(v.toFixed(2)));
}

const p = $derived({
	yTicks: 5,
	area: true,
	smooth: true,
	height: 220,
	showDots: true,
	strokeWidth: 2.5,
	width: "100%",
	...props,
});
const styleWidth = $derived(
	typeof p.width === "number" ? `${p.width}px` : p.width,
);
const c = $derived.by(() => {
	const data = p.data;
	const H = p.height;
	const padL = 48;
	const padR = 16;
	const padT = 16;
	const padB = 32;
	const W = 600;
	const innerW = W - padL - padR;
	const innerH = H - padT - padB;
	const values = data.map((d) => d.value);
	const minV = Math.min(0, ...values);
	const maxV = Math.max(...values, minV === 0 ? 1 : minV + 1);
	const ticks = niceTicks(minV, maxV, p.yTicks);
	const tMin = ticks[0];
	const tMax = ticks[ticks.length - 1];
	const yScale = (v: number) =>
		padT + innerH - ((v - tMin) / (tMax - tMin || 1)) * innerH;
	const xStep = data.length <= 1 ? innerW : innerW / (data.length - 1);
	const pts: [number, number][] = data.map((d, i) => [
		padL + (data.length === 1 ? innerW / 2 : i * xStep),
		yScale(d.value),
	]);
	const linePath = p.smooth ? buildSmoothPath(pts) : buildLinearPath(pts);
	const baseY = yScale(Math.max(0, tMin));
	const areaPath =
		pts.length > 0
			? `${linePath} L ${pts[pts.length - 1][0]} ${baseY} L ${pts[0][0]} ${baseY} Z`
			: "";
	const labelStep = data.length > 8 ? Math.ceil(data.length / 8) : 1;
	const color = p.color ?? PALETTE[0];
	return {
		W,
		H,
		padL,
		padR,
		padT,
		padB,
		ticks,
		pts,
		linePath,
		areaPath,
		baseY,
		labelStep,
		color,
		yScale,
		xStep,
		innerW,
	};
});
</script>

<div style="width:{styleWidth};display:block;">
	{#if p.title}
		<div style="font-size:13px;font-weight:700;color:hsl(var(--bc));margin-bottom:8px;text-align:left;">{p.title}</div>
	{/if}
	{#each [c] as cc}
		<svg viewBox="0 0 {cc.W} {cc.H}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:{cc.H}px;display:block;">
			{#each cc.ticks as t}
				{@const y = cc.yScale(t)}
				<line x1={cc.padL} x2={cc.W - cc.padR} y1={y} y2={y} stroke="hsl(var(--b3))" stroke-width={1} opacity={0.5} />
				<text x={cc.padL - 6} y={y + 4} text-anchor="end" font-size="11" fill="hsl(var(--bc) / 0.7)">{formatNum(t)}</text>
			{/each}
			{#if p.area && cc.areaPath}
				<path d={cc.areaPath} fill="color-mix(in srgb, {cc.color} 18%, transparent)" />
			{/if}
			{#if cc.linePath}
				<path d={cc.linePath} fill="none" stroke={cc.color} stroke-width={p.strokeWidth} stroke-linecap="round" stroke-linejoin="round" />
			{/if}
			{#if p.showDots}
				{#each cc.pts as pt, i}
					<circle cx={pt[0]} cy={pt[1]} r={3.5} fill={cc.color} stroke="#fff" stroke-width={1.5} />
				{/each}
			{/if}
			{#each p.data as d, i}
				{#if i % cc.labelStep === 0 || i === p.data.length - 1}
					{@const x = cc.padL + (p.data.length === 1 ? cc.innerW / 2 : i * cc.xStep)}
					<text x={x} y={cc.H - cc.padB + 18} text-anchor="middle" font-size="11" fill="hsl(var(--bc) / 0.7)">{d.label}</text>
				{/if}
			{/each}
		</svg>
	{/each}
</div>
