<script lang="ts">
// Task 8 - 通用后台页面骨架屏组件
// 结构：标题区（h1 + sub 两行） + 工具栏（左按钮 右搜索） + 2 行 x 4 列卡片区 + 6 行表格轮廓
export let title = "";
export let cards = 8;
export let tableRows = 6;
export let tableCols = 6;

function clamp(n: number, min: number, max: number): number {
	return Math.max(min, Math.min(max, n));
}

cards = clamp(cards ?? 8, 1, 16);
tableRows = clamp(tableRows ?? 6, 1, 20);
tableCols = clamp(tableCols ?? 6, 2, 12);
</script>

<div class="skel-page" role="status" aria-label="loading">
	<!-- 标题区 -->
	<div class="skel-header">
		<div class="skel-title-row">
			<div class="skel-title" style="width: {title ? '100%' : '42%'}; min-width: 180px; max-width: 420px;">
				{#if title}<span class="sr-only">{title}</span>{/if}
			</div>
			<div class="skel-sub" style="width: 36%; min-width: 140px; max-width: 360px; margin-top: 10px;"></div>
		</div>
		<!-- 工具栏 -->
		<div class="skel-toolbar">
			<div class="skel-tb-left">
				<div class="skel-btn skel-btn-primary" style="width: 108px;"></div>
				<div class="skel-btn" style="width: 92px;"></div>
				<div class="skel-btn" style="width: 86px;"></div>
			</div>
			<div class="skel-tb-right">
				<div class="skel-search" style="width: 220px;"></div>
				<div class="skel-btn" style="width: 84px;"></div>
			</div>
		</div>
	</div>

	<!-- 卡片区（2 行 4 列） -->
	<div class="skel-grid" style="--cols: {Math.min(4, Math.max(2, Math.min(cards, 4)))};">
		{#each Array(cards) as _ (Math.random())}
			<div class="skel-card">
				<div class="skel-card-top">
					<div class="skel-icon"></div>
					<div class="skel-card-head">
						<div class="skel-label" style="width: 58%;"></div>
						<div class="skel-value" style="width: 74%; margin-top: 6px;"></div>
					</div>
				</div>
				<div class="skel-card-foot" style="width: 42%; margin-top: 16px;"></div>
			</div>
		{/each}
	</div>

	<!-- 表格轮廓（6 行默认） -->
	<div class="skel-table-wrap">
		<div class="skel-table-head">
			{#each Array(tableCols) as _c (Math.random())}
				<div class="skel-th" style="width: {_c === 0 ? '32%' : _c === tableCols - 1 ? '18%' : `${Math.round(68 / (tableCols - 1))}%`};"></div>
			{/each}
		</div>
		{#each Array(tableRows) as _r (Math.random())}
			<div class="skel-table-row">
				{#each Array(tableCols) as _c2 (Math.random())}
					<div class="skel-td" style="width: {_c2 === 0 ? '32%' : _c2 === tableCols - 1 ? '18%' : `${Math.round(68 / (tableCols - 1))}%`};">
						<div class="skel-cell" style="height: {_c2 === 0 ? '16px' : '14px'}; width: {_c2 === 0 ? '78%' : _c2 === tableCols - 1 ? '46%' : '58%'};"></div>
					</div>
				{/each}
			</div>
		{/each}
		<div class="skel-pagination">
			<div class="skel-pag-info" style="width: 160px;"></div>
			<div class="skel-pag-buttons">
				<div class="skel-page-btn"></div>
				<div class="skel-page-btn"></div>
				<div class="skel-page-btn active"></div>
				<div class="skel-page-btn"></div>
				<div class="skel-page-btn"></div>
			</div>
		</div>
	</div>
</div>

<style>
	.skel-page {
		width: 100%;
	}

	.skel-header {
		margin-bottom: 28px;
	}

	.skel-title-row {
		display: flex;
		flex-direction: column;
	}

	.skel-title,
	.skel-sub,
	.skel-btn,
	.skel-search,
	.skel-label,
	.skel-value,
	.skel-card-foot,
	.skel-th,
	.skel-cell,
	.skel-page-btn,
	.skel-pag-info,
	.skel-icon {
		background: linear-gradient(
			90deg,
			hsl(var(--b2)) 0%,
			hsl(var(--b3)) 45%,
			hsl(var(--b3) / 0.8) 55%,
			hsl(var(--b2)) 100%
		);
		background-size: 200% 100%;
		animation: skel-shimmer 1.4s linear infinite;
		border-radius: 9999px;
	}

	.skel-title {
		height: 28px;
		border-radius: 10px;
	}

	.skel-sub {
		height: 14px;
		border-radius: 7px;
		opacity: 0.85;
	}

	.skel-toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 14px;
		flex-wrap: wrap;
		margin-top: 22px;
	}

	.skel-tb-left,
	.skel-tb-right {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}

	.skel-btn {
		height: 38px;
		border-radius: 12px;
		background-size: 260% 100%;
	}

	.skel-btn-primary {
		opacity: 0.92;
	}

	.skel-search {
		height: 38px;
		border-radius: 12px;
		background-size: 260% 100%;
	}

	.skel-grid {
		display: grid;
		grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr));
		gap: 18px;
		margin-bottom: 28px;
	}

	@media (max-width: 1100px) {
		.skel-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
	}
	@media (max-width: 820px) {
		.skel-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	}
	@media (max-width: 540px) {
		.skel-grid { grid-template-columns: 1fr; }
	}

	.skel-card {
		background: hsl(var(--b1));
		border: 1px solid hsl(var(--b3));
		border-radius: 18px;
		padding: 22px;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		min-height: 118px;
		overflow: hidden;
	}

	.skel-card-top {
		display: flex;
		align-items: flex-start;
		gap: 14px;
	}

	.skel-icon {
		width: 50px;
		height: 50px;
		border-radius: 14px;
		flex-shrink: 0;
		background-size: 260% 100%;
	}

	.skel-card-head {
		flex: 1;
		min-width: 0;
	}

	.skel-label {
		height: 13px;
	}

	.skel-value {
		height: 28px;
		border-radius: 10px;
	}

	.skel-card-foot {
		height: 12px;
	}

	.skel-table-wrap {
		background: hsl(var(--b1));
		border: 1px solid hsl(var(--b3));
		border-radius: 18px;
		overflow: hidden;
	}

	.skel-table-head {
		display: flex;
		gap: 18px;
		padding: 15px 24px;
		background: hsl(var(--b2));
		border-bottom: 1px solid hsl(var(--b3));
	}

	.skel-th {
		height: 11px;
		background-size: 260% 100%;
	}

	.skel-table-row {
		display: flex;
		gap: 18px;
		padding: 16px 24px;
		border-bottom: 1px solid hsl(var(--b3) / 0.55);
		align-items: center;
	}

	.skel-table-row:last-child {
		border-bottom: none;
	}

	.skel-td {
		min-width: 0;
	}

	.skel-cell {
		height: 14px;
		background-size: 260% 100%;
	}

	.skel-pagination {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 24px;
		border-top: 1px solid hsl(var(--b3));
		gap: 14px;
		flex-wrap: wrap;
	}

	.skel-pag-info {
		height: 13px;
	}

	.skel-pag-buttons {
		display: flex;
		gap: 5px;
	}

	.skel-page-btn {
		width: 36px;
		height: 36px;
		border-radius: 10px;
		background-size: 260% 100%;
	}

	.skel-page-btn.active {
		opacity: 0.9;
	}

	@keyframes skel-shimmer {
		0%   { background-position: 200% 0; }
		100% { background-position: -200% 0; }
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	@media (prefers-reduced-motion: reduce) {
		.skel-title,
		.skel-sub,
		.skel-btn,
		.skel-search,
		.skel-label,
		.skel-value,
		.skel-card-foot,
		.skel-th,
		.skel-cell,
		.skel-page-btn,
		.skel-pag-info,
		.skel-icon {
			animation: none;
		}
	}
</style>
