<script lang="ts">
type Props = {
	data: number[];
	height?: number;
	width?: number;
	color?: string;
	showArea?: boolean;
	showEndDot?: boolean;
};
let props: Props = $props();

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

const p = $derived({
	height: 32,
	width: 120,
	color: "var(--ochre-500)",
	showArea: true,
	showEndDot: true,
	...props,
});
const c = $derived.by(() => {
	const data = p.data;
	if (data.length === 0)
		return {
			linePath: "",
			areaPath: "",
			endPt: null as [number, number] | null,
			W: p.width,
			H: p.height,
		};
	const W = p.width;
	const H = p.height;
	const pad = 2;
	const innerW = W - pad * 2;
	const innerH = H - pad * 2;
	const minV = Math.min(...data);
	const maxV = Math.max(...data);
	const range = maxV - minV || 1;
	const xStep = data.length <= 1 ? innerW : innerW / (data.length - 1);
	const pts: [number, number][] = data.map((v, i) => [
		pad + (data.length === 1 ? innerW / 2 : i * xStep),
		pad + innerH - ((v - minV) / range) * innerH,
	]);
	const linePath = buildSmoothPath(pts);
	const areaPath = `${linePath} L ${pts[pts.length - 1][0]} ${H} L ${pts[0][0]} ${H} Z`;
	const endPt = pts[pts.length - 1];
	return { linePath, areaPath, endPt, W, H };
});
</script>

{#each [c] as cc}
	<div style="width:{p.width}px;height:{p.height}px;display:inline-block;">
		<svg viewBox="0 0 {cc.W} {cc.H}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%;display:block;">
			{#if p.showArea && cc.areaPath}
				<path d={cc.areaPath} fill="color-mix(in srgb, {p.color} 20%, transparent)" />
			{/if}
			{#if cc.linePath}
				<path d={cc.linePath} fill="none" stroke={p.color} stroke-width={1.5} stroke-linecap="round" stroke-linejoin="round" />
			{/if}
			{#if p.showEndDot && cc.endPt}
				<circle cx={cc.endPt[0]} cy={cc.endPt[1]} r={2.5} fill={p.color} />
			{/if}
		</svg>
	</div>
{/each}
