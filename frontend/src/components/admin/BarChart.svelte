<script lang="ts">
type Props = {
	data: { label: string; value: number; color?: string }[];
	horizontal?: boolean;
	height?: number;
	barRadius?: number;
	barGap?: number;
	yTicks?: number;
	valueFormatter?: (v: number) => string;
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
function formatNum(v: number): string {
	const abs = Math.abs(v);
	if (abs >= 1e9) return `${(v / 1e9).toFixed(1).replace(/\.0$/, "")}B`;
	if (abs >= 1e6) return `${(v / 1e6).toFixed(1).replace(/\.0$/, "")}M`;
	if (abs >= 1e3) return `${(v / 1e3).toFixed(1).replace(/\.0$/, "")}K`;
	return String(Number(v.toFixed(2)));
}
const p = $derived({
	horizontal: false,
	height: 240,
	barRadius: 6,
	barGap: 0.4,
	yTicks: 4,
	width: "100%",
	...props,
});
const fmt = $derived(p.valueFormatter ?? ((v: number) => formatNum(v)));
const styleWidth = $derived(
	typeof p.width === "number" ? `${p.width}px` : p.width,
);
const c = $derived.by(() => {
	const H = p.height;
	const W = 600;
	const n = p.data.length;
	const padL = p.horizontal ? 96 : 48;
	const padR = 16;
	const padT = 16;
	const padB = p.horizontal ? 28 : 56;
	const innerW = W - padL - padR;
	const innerH = H - padT - padB;
	const values = p.data.map((d) => d.value);
	const minV = Math.min(0, ...values);
	const maxV = Math.max(...values, minV === 0 ? 1 : minV + 1);
	const ticks = niceTicks(minV, maxV, p.yTicks);
	const tMin = ticks[0];
	const tMax = ticks[ticks.length - 1];
	const range = tMax - tMin || 1;
	const bars = p.data.map((d, i) => ({
		...d,
		color: d.color ?? PALETTE[i % PALETTE.length],
		rawIndex: i,
	}));
	return {
		W,
		H,
		n,
		padL,
		padR,
		padT,
		padB,
		innerW,
		innerH,
		ticks,
		tMin,
		tMax,
		range,
		bars,
	};
});
</script>

<div style="width:{styleWidth};display:block;">
	{#if p.title}
		<div style="font-size:13px;font-weight:700;color:hsl(var(--bc));margin-bottom:8px;text-align:left;">{p.title}</div>
	{/if}
	{#each [c] as cc}
		<svg viewBox="0 0 {cc.W} {cc.H}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:{cc.H}px;display:block;">
			{#if !p.horizontal}
				{#each cc.ticks as t}
					{@const y = cc.padT + cc.innerH - ((t - cc.tMin) / cc.range) * cc.innerH}
					<line x1={cc.padL} x2={cc.W - cc.padR} y1={y} y2={y} stroke="hsl(var(--b3))" stroke-width={1} opacity={0.5} />
					<text x={cc.padL - 6} y={y + 4} text-anchor="end" font-size="11" fill="hsl(var(--bc) / 0.7)">{formatNum(t)}</text>
				{/each}
				{#if cc.n > 0}
					{@const slotSize = cc.innerW / cc.n}
					{@const barSize = slotSize * (1 - p.barGap)}
					{@const gap = slotSize * p.barGap}
					{@const zeroY = cc.padT + cc.innerH - ((Math.max(0, cc.tMin) - cc.tMin) / cc.range) * cc.innerH}
					{#each cc.bars as b, i}
						{@const barH = Math.max(Math.abs(((b.value - cc.tMin) / cc.range) * cc.innerH - ((Math.max(0, cc.tMin) - cc.tMin) / cc.range) * cc.innerH), 0.5)}
						{@const x = cc.padL + i * slotSize + gap / 2}
						{@const y = b.value >= 0 ? zeroY - barH : zeroY}
						{@const rotate = cc.n > 6}
						{@const labelX = x + barSize / 2}
						{@const labelY = cc.H - cc.padB + 16}
						<g>
							<rect x={x} y={y} width={barSize} height={barH} rx={p.barRadius} fill={b.color}>
								<title>{b.label}: {fmt(b.value)}</title>
							</rect>
							<text x={labelX} y={rotate ? labelY + 4 : labelY} text-anchor="middle" font-size="11" fill="hsl(var(--bc) / 0.7)" transform={rotate ? `rotate(-20 ${labelX} ${labelY})` : undefined}>
								{b.label}
							</text>
						</g>
					{/each}
				{/if}
			{:else}
				{#each cc.ticks as t}
					{@const x = cc.padL + ((t - cc.tMin) / cc.range) * cc.innerW}
					<line x1={x} x2={x} y1={cc.padT} y2={cc.H - cc.padB} stroke="hsl(var(--b3))" stroke-width={1} opacity={0.5} />
					<text x={x} y={cc.H - cc.padB + 16} text-anchor="middle" font-size="11" fill="hsl(var(--bc) / 0.7)">{formatNum(t)}</text>
				{/each}
				{#if cc.n > 0}
					{@const vSlot = cc.innerH / Math.max(1, cc.n)}
					{@const vBarSize = vSlot * (1 - p.barGap)}
					{@const vGap = vSlot * p.barGap}
					{@const zeroX = cc.padL + ((Math.max(0, cc.tMin) - cc.tMin) / cc.range) * cc.innerW}
					{#each cc.bars as b, i}
						{@const bw = Math.max(Math.abs(((b.value - cc.tMin) / cc.range) * cc.innerW - ((Math.max(0, cc.tMin) - cc.tMin) / cc.range) * cc.innerW), 0.5)}
						{@const y = cc.padT + i * vSlot + vGap / 2}
						{@const x = b.value >= 0 ? zeroX : zeroX - bw}
						{@const labelX = cc.padL - 8}
						{@const labelY = y + vBarSize / 2 + 4}
						<g>
							<rect x={x} y={y} width={bw} height={vBarSize} rx={p.barRadius} fill={b.color}>
								<title>{b.label}: {fmt(b.value)}</title>
							</rect>
							<text x={labelX} y={labelY} text-anchor="end" font-size="11" fill="hsl(var(--bc) / 0.7)">{b.label}</text>
						</g>
					{/each}
				{/if}
			{/if}
		</svg>
	{/each}
</div>
