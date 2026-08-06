<script lang="ts">
type HeatmapCell = { date: string; value: number };
type Props = {
	data: HeatmapCell[];
	endDate?: string;
	months?: number;
	cellSize?: number;
	cellGap?: number;
	title?: string;
	width?: string | number;
};
let props: Props = $props();

const p = $derived({
	months: 12,
	cellSize: 12,
	cellGap: 3,
	width: "100%",
	...props,
});
const styleWidth = $derived(
	typeof p.width === "number" ? `${p.width}px` : p.width,
);
const c = $derived.by(() => {
	const end = p.endDate ? new Date(`${p.endDate}T00:00:00`) : new Date();
	end.setHours(0, 0, 0, 0);
	const start = new Date(end);
	start.setMonth(start.getMonth() - p.months);
	start.setHours(0, 0, 0, 0);
	const dow = (start.getDay() + 6) % 7;
	const gridStart = new Date(start);
	gridStart.setDate(gridStart.getDate() - dow);
	const gridEnd = new Date(end);
	const endDow = (gridEnd.getDay() + 6) % 7;
	gridEnd.setDate(gridEnd.getDate() + (6 - endDow));
	const totalDays =
		Math.round((gridEnd.getTime() - gridStart.getTime()) / 86400000) + 1;
	const totalWeeks = Math.ceil(totalDays / 7);
	const weeks = Math.min(totalWeeks, 53);
	const valueMap = new Map<string, number>();
	let maxV = 0;
	for (const d of p.data) {
		valueMap.set(d.date, d.value);
		if (d.value > maxV) maxV = d.value;
	}
	const levelColor = (v: number): string => {
		if (v <= 0 || maxV <= 0) return "hsl(var(--b3))";
		const pct = v / maxV;
		if (pct <= 0.25)
			return "color-mix(in srgb, var(--ochre-300) 35%, transparent)";
		if (pct <= 0.5)
			return "color-mix(in srgb, var(--ochre-400) 55%, transparent)";
		if (pct <= 0.75) return "var(--ochre-400)";
		return "var(--ochre-600)";
	};
	const leftPad = 24;
	const topPad = 20;
	const gridW = weeks * (p.cellSize + p.cellGap);
	const gridH = 7 * (p.cellSize + p.cellGap);
	const W = leftPad + gridW + 4;
	const H = topPad + gridH + 4;
	const cells: {
		x: number;
		y: number;
		date: string;
		value: number;
		color: string;
	}[] = [];
	for (let w = 0; w < weeks; w++) {
		for (let d = 0; d < 7; d++) {
			const day = new Date(gridStart);
			day.setDate(gridStart.getDate() + w * 7 + d);
			const dateStr = day.toISOString().slice(0, 10);
			const val = valueMap.get(dateStr) ?? 0;
			const inRange = day >= start && day <= end;
			if (!inRange) continue;
			const x = leftPad + w * (p.cellSize + p.cellGap);
			const y = topPad + d * (p.cellSize + p.cellGap);
			cells.push({ x, y, date: dateStr, value: val, color: levelColor(val) });
		}
	}
	const monthLabels: { x: number; label: string }[] = [];
	let lastMonth = -1;
	for (let w = 0; w < weeks; w++) {
		const day = new Date(gridStart);
		day.setDate(gridStart.getDate() + w * 7);
		if (day < start) continue;
		const m = day.getMonth();
		if (m !== lastMonth) {
			lastMonth = m;
			monthLabels.push({
				x: leftPad + w * (p.cellSize + p.cellGap),
				label: `${m + 1}月`,
			});
		}
	}
	const weekdayLabels = ["一", "", "三", "", "五", "", "日"];
	return {
		W,
		H,
		cells,
		monthLabels,
		weekdayLabels,
		topPad,
		leftPad,
		cellSize: p.cellSize,
	};
});
</script>

<div style="width:{styleWidth};overflow:auto;display:block;">
	{#if p.title}
		<div style="font-size:13px;font-weight:700;color:hsl(var(--bc));margin-bottom:8px;text-align:left;">{p.title}</div>
	{/if}
	{#each [c] as cc}
		<svg viewBox="0 0 {cc.W} {cc.H}" preserveAspectRatio="xMidYMid meet" style="width:100%;height:{cc.H}px;display:block;min-width:{cc.W}px;">
			{#each cc.monthLabels as m, i}
				<text x={m.x} y={cc.topPad - 6} text-anchor="start" font-size="10" fill="hsl(var(--bc) / 0.7)">{m.label}</text>
			{/each}
			{#each cc.weekdayLabels as lbl, i}
				{#if lbl}
					<text x={cc.leftPad - 4} y={cc.topPad + i * (p.cellSize + p.cellGap) + p.cellSize - 2} text-anchor="end" font-size="10" fill="hsl(var(--bc) / 0.7)">{lbl}</text>
				{/if}
			{/each}
			{#each cc.cells as cell, i}
				<rect x={cell.x} y={cell.y} width={cc.cellSize} height={cc.cellSize} rx={2} fill={cell.color}>
					<title>{cell.date}: {cell.value}</title>
				</rect>
			{/each}
		</svg>
	{/each}
</div>
