<script lang="ts">
export interface Column<T> {
	key: keyof T | string;
	title: string;
	width?: string | number;
	sortable?: boolean;
	searchable?: boolean;
	align?: "left" | "center" | "right";
	ellipsis?: boolean;
	render?: (row: T, rowIndex: number) => string;
	className?: string;
}

export interface DataTableSelectionEvent<T> {
	keys: (string | number)[];
	rows: T[];
}

export interface FilterOption {
	key: string;
	label: string;
}

export interface DataTableProps<T> {
	data?: T[];
	columns?: Column<T>[];
	rowKey?: keyof T | ((row: T) => string | number);
	searchable?: boolean;
	searchPlaceholder?: string;
	sortable?: boolean;
	pagination?: boolean;
	pageSize?: number;
	pageSizeOptions?: number[];
	selectable?: boolean;
	selectedKeys?: (string | number)[];
	toolbarRight?: string;
	onSelectionChange?: (ev: DataTableSelectionEvent<T>) => void;
	onRowClick?: (row: T) => void;
	emptyTitle?: string;
	emptyDesc?: string;
	stickyHeader?: boolean;
	compact?: boolean;
	zebra?: boolean;
	bordered?: boolean;
	height?: string | number;
	className?: string;
	loading?: boolean;
	filterOptions?: FilterOption[];
	activeFilter?: string;
	onFilterChange?: (key: string) => void;
}

let {
	data = [],
	columns = [],
	rowKey = "id",
	searchable = true,
	searchPlaceholder = "搜索…",
	sortable = true,
	pagination = true,
	pageSize = 20,
	pageSizeOptions = [10, 20, 50, 100],
	selectable = false,
	selectedKeys = undefined,
	toolbarRight = "",
	onSelectionChange = undefined,
	onRowClick = undefined,
	emptyTitle = "暂无数据",
	emptyDesc = "",
	stickyHeader = true,
	compact = false,
	zebra = true,
	bordered = false,
	height = 520,
	className = "",
	loading = false,
	filterOptions = undefined,
	activeFilter = undefined,
	onFilterChange = undefined,
} = $props<any>();

/* ===================== 工具函数 ===================== */
function getNested(obj: any, path: string): any {
	if (obj == null) return undefined;
	const keys = path.split(".");
	let cur = obj;
	for (const k of keys) {
		if (cur == null) return undefined;
		cur = cur[k];
	}
	return cur;
}

function isSearchableValue(v: any): boolean {
	return typeof v === "string" || typeof v === "number";
}

function getKey(row: any, index: number): string | number {
	try {
		if (typeof rowKey === "function") {
			const k = (rowKey as any)(row);
			if (k !== undefined && k !== null) return k;
		} else {
			const k = row[rowKey as any];
			if (k !== undefined && k !== null) return k;
		}
	} catch {
		/* ignore */
	}
	return index;
}

/* ===================== 核心状态 ===================== */
let searchText = $state("");
let sortKey = $state<string | null>(null);
let sortDir = $state<"asc" | "desc" | null>(null);
let currentPage = $state(1);
let internalPageSize = $state(pageSize);
let internalSelected = $state<Set<string | number>>(new Set());
let jumpInput = $state("");
let prevSearch = $state("");
let prevSortKey = $state<string | null>(null);
let prevSortDir = $state<"asc" | "desc" | null>(null);
let prevPageSize = $state(pageSize);
let internalFilter = $state<string>("all");

const defaultFilterOptions: FilterOption[] = [
	{ key: "all", label: "全部" },
	{ key: "published", label: "已发布" },
	{ key: "draft", label: "草稿" },
];

const resolvedFilterOptions = $derived.by(
	() => filterOptions ?? defaultFilterOptions,
);
const resolvedActiveFilter = $derived.by(() => activeFilter ?? internalFilter);

function handleFilterClick(key: string) {
	if (activeFilter === undefined) {
		internalFilter = key;
	}
	onFilterChange?.(key);
}

/* ===================== 派生数据 ===================== */
const filteredData = $derived.by(() => {
	const list: any[] = data || [];
	const q = searchText.trim().toLowerCase();
	if (!q) return list;
	const cols = (columns || []).filter((c: any) => c.searchable !== false);
	return list.filter((row) => {
		for (const col of cols) {
			const v = getNested(row, String(col.key));
			if (isSearchableValue(v) && String(v).toLowerCase().includes(q)) {
				return true;
			}
		}
		return false;
	});
});

const sortedData = $derived.by(() => {
	const list = filteredData.slice();
	if (!sortKey || !sortDir) return list;
	const dir = sortDir === "asc" ? 1 : -1;
	list.sort((a: any, b: any) => {
		const va = getNested(a, sortKey);
		const vb = getNested(b, sortKey);
		if (va == null && vb == null) return 0;
		if (va == null) return 1;
		if (vb == null) return -1;
		if (typeof va === "number" && typeof vb === "number") {
			return (va - vb) * dir;
		}
		return String(va).localeCompare(String(vb)) * dir;
	});
	return list;
});

const totalPages = $derived.by(() => {
	const n = sortedData.length;
	if (!pagination || internalPageSize <= 0) return n > 0 ? 1 : 0;
	return Math.max(1, Math.ceil(n / internalPageSize));
});

const pageData = $derived.by(() => {
	if (!pagination) return sortedData;
	const ps = internalPageSize;
	const start = Math.max(0, currentPage - 1) * ps;
	return sortedData.slice(start, start + ps);
});

const pageButtons = $derived.by(() => {
	const tp = totalPages;
	if (tp <= 0) return [] as (number | "...")[];
	const cur = Math.min(Math.max(1, currentPage), tp);
	if (tp <= 7) {
		const arr: (number | "...")[] = [];
		for (let i = 1; i <= tp; i++) arr.push(i);
		return arr;
	}
	const result: (number | "...")[] = [];
	const left = Math.max(2, cur - 2);
	const right = Math.min(tp - 1, cur + 2);
	result.push(1);
	if (left > 2) result.push("...");
	for (let i = left; i <= right; i++) result.push(i);
	if (right < tp - 1) result.push("...");
	result.push(tp);
	return result;
});

const computedSelected = $derived.by(() => {
	if (selectedKeys !== undefined && Array.isArray(selectedKeys)) {
		return new Set<string | number>(selectedKeys);
	}
	return internalSelected;
});

const isAllSelected = $derived.by(() => {
	if (!selectable || sortedData.length === 0) return false;
	for (let i = 0; i < sortedData.length; i++) {
		const k = getKey(sortedData[i], i);
		if (!computedSelected.has(k)) return false;
	}
	return true;
});

const isIndeterminate = $derived.by(() => {
	if (!selectable || sortedData.length === 0) return false;
	let has = false;
	let hasNot = false;
	for (let i = 0; i < sortedData.length; i++) {
		const k = getKey(sortedData[i], i);
		if (computedSelected.has(k)) has = true;
		else hasNot = true;
		if (has && hasNot) return true;
	}
	return false;
});

/* ===================== 副作用 ===================== */
$effect(() => {
	internalPageSize = pageSize;
});

$effect(() => {
	const s = searchText;
	const sk = sortKey;
	const sd = sortDir;
	const ps = internalPageSize;
	if (
		s !== prevSearch ||
		sk !== prevSortKey ||
		sd !== prevSortDir ||
		ps !== prevPageSize
	) {
		currentPage = 1;
		prevSearch = s;
		prevSortKey = sk;
		prevSortDir = sd;
		prevPageSize = ps;
	}
});

$effect(() => {
	if (selectedKeys !== undefined && Array.isArray(selectedKeys)) {
		internalSelected = new Set(selectedKeys);
	}
});

$effect(() => {
	if (!onSelectionChange) return;
	const sel = computedSelected;
	const keys: (string | number)[] = [];
	const rows: any[] = [];
	const list = data || [];
	for (let i = 0; i < list.length; i++) {
		const k = getKey(list[i], i);
		if (sel.has(k)) {
			keys.push(k);
			rows.push(list[i]);
		}
	}
	onSelectionChange({ keys, rows });
});

/* ===================== 交互逻辑 ===================== */
function toggleSort(col: any) {
	const canSort = sortable ? col.sortable !== false : col.sortable === true;
	if (!canSort) return;
	const k = String(col.key);
	if (sortKey !== k) {
		sortKey = k;
		sortDir = "asc";
	} else if (sortDir === "asc") {
		sortDir = "desc";
	} else if (sortDir === "desc") {
		sortKey = null;
		sortDir = null;
	} else {
		sortDir = "asc";
	}
}

function goToPage(p: number) {
	const tp = totalPages;
	if (tp <= 0) return;
	currentPage = Math.min(Math.max(1, p), tp);
}

function changePageSize(ps: number) {
	internalPageSize = ps;
}

function handleJump() {
	const v = Number.parseInt(jumpInput, 10);
	if (!Number.isNaN(v)) {
		goToPage(v);
	}
	jumpInput = "";
}

function toggleRowSelected(row: any, idx: number) {
	const k = getKey(row, idx);
	if (selectedKeys === undefined) {
		const next = new Set(internalSelected);
		if (next.has(k)) next.delete(k);
		else next.add(k);
		internalSelected = next;
	} else if (onSelectionChange) {
		const cur = new Set<string | number>(selectedKeys || []);
		if (cur.has(k)) cur.delete(k);
		else cur.add(k);
		const keys: (string | number)[] = [];
		const rows: any[] = [];
		for (let i = 0; i < data.length; i++) {
			const rk = getKey(data[i], i);
			if (cur.has(rk)) {
				keys.push(rk);
				rows.push(data[i]);
			}
		}
		onSelectionChange({ keys, rows });
	}
}

function toggleSelectAll() {
	const list = sortedData;
	if (list.length === 0) return;
	const next = new Set<string | number>();
	if (!isAllSelected) {
		for (let i = 0; i < list.length; i++) {
			next.add(getKey(list[i], i));
		}
		if (selectedKeys === undefined) {
			internalSelected = next;
		} else if (onSelectionChange) {
			const keys: (string | number)[] = [];
			const rows: any[] = [];
			for (let i = 0; i < data.length; i++) {
				const rk = getKey(data[i], i);
				if (next.has(rk)) {
					keys.push(rk);
					rows.push(data[i]);
				}
			}
			onSelectionChange({ keys, rows });
		}
	} else {
		if (selectedKeys === undefined) {
			internalSelected = new Set();
		} else if (onSelectionChange) {
			onSelectionChange({ keys: [], rows: [] });
		}
	}
}

function setHeaderCb(el: HTMLInputElement) {
	if (!el) return;
	el.indeterminate = isIndeterminate;
	el.checked = isAllSelected;
}
</script>

<div class:list={['dt-container', className ? className : '']}>
	{#if searchable || toolbarRight || resolvedFilterOptions.length > 0}
		<div class="dt-toolbar">
			<div class="dt-toolbar-left">
				{#if searchable}
					<div class="dt-search">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="dt-search-icon"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
						<input
							type="text"
							bind:value={searchText}
							placeholder={searchPlaceholder}
							class="dt-search-input" />
					</div>
				{/if}
				{#if resolvedFilterOptions.length > 0}
					<div class="dt-segmented">
						{#each resolvedFilterOptions as opt (opt.key)}
							<button
								type="button"
								class="dt-segmented-item"
								class:active={resolvedActiveFilter === opt.key}
								on:click={() => handleFilterClick(opt.key)}
							>{opt.label}</button>
						{/each}
					</div>
				{/if}
			</div>
			<div class="dt-toolbar-right">
				{#if toolbarRight}
					{@html toolbarRight}
				{/if}
			</div>
		</div>
	{/if}

	<div class="dt-scroll" class:dt-sticky-header={stickyHeader} style:max-height={typeof height === 'number' ? `${height}px` : String(height)}>
		<table class="dt-table" class:dt-bordered={bordered} class:dt-zebra={zebra} class:dt-compact={compact}>
		<thead>
			<tr>
				{#if selectable}
					<th class="dt-th dt-th-check">
						<input type="checkbox" class="dt-checkbox" on:change={toggleSelectAll} use:setHeaderCb />
					</th>
				{/if}
				{#each columns as col (String(col.key))}
					{@const colSortable = sortable ? col.sortable !== false : col.sortable === true}
					{@const active = sortKey === String(col.key)}
					<th
						class:list={[
							'dt-th',
							col.align ? `dt-align-${col.align}` : '',
							col.className ? col.className : '',
							colSortable ? 'dt-sortable' : '',
							active ? 'dt-sort-active' : ''
						]}
						style:width={col.width ? (typeof col.width === 'number' ? `${col.width}px` : String(col.width)) : undefined}
						on:click={() => colSortable && toggleSort(col)}
					>
						<span class="dt-th-inner">
							{col.title}
							{#if colSortable}
								<span class="dt-sort-arrows">
									<span class="dt-arrow dt-arrow-up" class:active={active && sortDir === 'asc'}>▲</span>
									<span class="dt-arrow dt-arrow-down" class:active={active && sortDir === 'desc'}>▼</span>
								</span>
							{/if}
						</span>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#if loading}
				{#each 6 as _, i (i)}
					<tr class="dt-tr dt-skeleton-row">
						{#if selectable}
							<td class="dt-td dt-td-check">
								<div class="dt-skeleton dt-skeleton-checkbox"></div>
							</td>
						{/if}
						{#each columns as col, ci (String(col.key))}
							<td class="dt-td">
								<div class="dt-skeleton" style:width={ci === 0 ? '40%' : `${30 + (ci % 3) * 20}%`}></div>
							</td>
						{/each}
					</tr>
				{/each}
			{:else if pageData.length === 0}
				<tr>
					<td colspan={selectable ? columns.length + 1 : columns.length} class="dt-empty-cell">
						<div class="dt-empty">
							<svg viewBox="0 0 120 120" class="dt-empty-icon" fill="none" xmlns="http://www.w3.org/2000/svg">
								<rect x="20" y="28" width="80" height="64" rx="10" stroke="currentColor" stroke-width="4" />
								<path d="M20 46h80" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
								<path d="M42 66h36" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.5"/>
								<path d="M42 82h24" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.35"/>
							</svg>
							{#if emptyTitle}
								<div class="dt-empty-title">{emptyTitle}</div>
							{/if}
							{#if emptyDesc}
								<div class="dt-empty-desc">{emptyDesc}</div>
							{/if}
						</div>
					</td>
				</tr>
			{:else}
				{#each pageData as row, idx (getKey(row, idx))}
					{@const rowIdx = (currentPage - 1) * internalPageSize + idx}
					<tr
						class="dt-tr"
						on:click={() => onRowClick?.(row)}
					>
						{#if selectable}
							<td class="dt-td dt-td-check" on:click|stopPropagation>
								<input
									type="checkbox"
									class="dt-checkbox"
									checked={computedSelected.has(getKey(row, rowIdx))}
									on:change={() => toggleRowSelected(row, rowIdx)}
								/>
							</td>
						{/if}
						{#each columns as col (String(col.key))}
							{@const rawVal = getNested(row, String(col.key))}
							<td
								class:list={[
									'dt-td',
									col.align ? `dt-align-${col.align}` : '',
									col.ellipsis === false ? '' : 'dt-ellipsis',
									col.className ? col.className : ''
								]}
								style:width={col.width ? (typeof col.width === 'number' ? `${col.width}px` : String(col.width)) : undefined}
							>
								{#if col.render}
									{@html col.render(row, rowIdx)}
								{:else}
									{rawVal ?? ''}
								{/if}
							</td>
						{/each}
					</tr>
				{/each}
			{/if}
		</tbody>
	</table>
	</div>

	{#if pagination}
		<div class="dt-pagination">
			<div class="dt-pag-left">
				<select class="dt-select" on:change={(e) => changePageSize(parseInt((e.target as HTMLSelectElement).value, 10))}>
					{#each pageSizeOptions as opt (opt)}
						<option value={opt} selected={internalPageSize === opt}>{opt} 条/页</option>
					{/each}
				</select>
				<span class="dt-pag-info">共 <strong>{sortedData.length}</strong> 条</span>
			</div>

			<div class="dt-pag-buttons">
				<button class="dt-page-btn" type="button" on:click={() => goToPage(currentPage - 1)} disabled={currentPage <= 1} title="上一页">
					<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
				</button>
				{#each pageButtons as btn, bIdx (bIdx)}
					{#if btn === '...'}
						<span class="dt-page-ellipsis">…</span>
					{:else}
						<button
							class="dt-page-btn"
							class:active={currentPage === btn}
							type="button"
							on:click={() => goToPage(btn as number)}
						>{btn}</button>
					{/if}
				{/each}
				<button class="dt-page-btn" type="button" on:click={() => goToPage(currentPage + 1)} disabled={currentPage >= totalPages} title="下一页">
					<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
				</button>
			</div>

			<div class="dt-pag-right">
				<div class="dt-jump">
					跳至
					<input
						type="text"
						class="dt-jump-input"
						bind:value={jumpInput}
						on:keydown={(e) => { if (e.key === 'Enter') handleJump(); }}
						placeholder=""
					/>
					页
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
.dt-container {
	width: 100%;
	background: #ffffff;
	overflow: hidden;
}

/* ============ Toolbar ============ */
.dt-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	flex-wrap: wrap;
	padding: 16px 24px;
}

.dt-toolbar-left,
.dt-toolbar-right {
	display: flex;
	align-items: center;
	gap: 12px;
	flex-wrap: wrap;
}

.dt-toolbar-right { margin-left: auto; }

.dt-search {
	position: relative;
	display: inline-flex;
	align-items: center;
}

.dt-search-icon {
	position: absolute;
	left: 12px;
	top: 50%;
	transform: translateY(-50%);
	width: 14px;
	height: 14px;
	color: #bfbfbf;
	pointer-events: none;
	z-index: 1;
}

.dt-search-input {
	height: 32px;
	padding: 4px 12px 4px 32px;
	border: 1px solid #d9d9d9;
	background: #ffffff;
	border-radius: 4px;
	font-size: 14px;
	color: #000000d9;
	outline: none;
	width: 220px;
	transition: all 0.2s ease-in-out;
	font-family: inherit;
	line-height: 1.5715;
}

.dt-search-input:hover {
	border-color: #4096ff;
}

.dt-search-input:focus {
	border-color: #1677ff;
	box-shadow: 0 0 0 2px rgba(5, 145, 255, 0.1);
}

.dt-search-input::placeholder {
	color: #00000040;
}

/* ============ Segmented ============ */
.dt-segmented {
	display: inline-flex;
	align-items: center;
	padding: 2px;
	background: #f5f5f5;
	border-radius: 6px;
	gap: 0;
}

.dt-segmented-item {
	height: 28px;
	padding: 0 16px;
	border: none;
	background: transparent;
	border-radius: 4px;
	font-size: 14px;
	font-weight: 400;
	color: #000000a6;
	cursor: pointer;
	transition: all 0.2s ease;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	font-family: inherit;
	line-height: 1;
}

.dt-segmented-item:hover {
	color: #000000d9;
}

.dt-segmented-item.active {
	background: #ffffff;
	color: #000000d9;
	font-weight: 500;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 1px rgba(0, 0, 0, 0.04);
}

/* ============ Primary Button ============ */
.dt-btn-primary {
	height: 32px;
	padding: 4px 15px;
	border: 1px solid #1677ff;
	background: #1677ff;
	color: #ffffff;
	border-radius: 4px;
	font-size: 14px;
	font-weight: 400;
	cursor: pointer;
	transition: all 0.2s ease;
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-family: inherit;
	line-height: 1.5715;
	text-shadow: 0 -1px 0 rgba(0, 0, 0, 0.12);
	box-shadow: 0 2px 0 rgba(5, 145, 255, 0.1);
}

.dt-btn-primary:hover {
	background: #4096ff;
	border-color: #4096ff;
}

.dt-btn-primary:active {
	background: #0958d9;
	border-color: #0958d9;
}

/* ============ Action Links ============ */
.dt-actions {
	display: inline-flex;
	align-items: center;
	gap: 16px;
}

.dt-link-edit {
	color: #1677ff;
	font-size: 14px;
	cursor: pointer;
	text-decoration: none;
	background: none;
	border: none;
	padding: 0;
	font-family: inherit;
	transition: color 0.2s ease;
}

.dt-link-edit:hover {
	color: #4096ff;
	text-decoration: underline;
}

.dt-link-delete {
	color: #ff4d4f;
	font-size: 14px;
	cursor: pointer;
	text-decoration: none;
	background: none;
	border: none;
	padding: 0;
	font-family: inherit;
	transition: color 0.2s ease;
}

.dt-link-delete:hover {
	color: #ff7875;
	text-decoration: underline;
}

/* ============ Scroll / Table ============ */
.dt-scroll {
	overflow: auto;
	position: relative;
}

.dt-table {
	width: 100%;
	border-collapse: separate;
	border-spacing: 0;
	min-width: 100%;
}

.dt-th {
	font-size: 14px;
	font-weight: 600;
	text-transform: none;
	letter-spacing: 0;
	color: #000000d9;
	background: #fafafa;
	border-bottom: 2px solid #f0f0f0;
	padding: 16px 24px;
	text-align: left;
	vertical-align: middle;
	white-space: nowrap;
	user-select: none;
	position: relative;
}

.dt-th::before {
	content: '';
	position: absolute;
	top: 50%;
	right: 0;
	width: 1px;
	height: 1.6em;
	background: transparent;
	transform: translateY(-50%);
}

.dt-compact .dt-th {
	padding: 12px 16px;
}

.dt-th.dt-th-check,
.dt-td.dt-td-check {
	width: 48px;
	padding-left: 24px;
	padding-right: 16px;
	text-align: left;
}

.dt-compact .dt-th.dt-th-check,
.dt-compact .dt-td.dt-td-check {
	width: 40px;
	padding-left: 16px;
	padding-right: 12px;
}

.dt-sortable { cursor: pointer; }

.dt-th-inner {
	display: inline-flex;
	align-items: center;
	gap: 8px;
}

.dt-sort-arrows {
	display: inline-flex;
	flex-direction: column;
	line-height: 1;
	font-size: 8px;
	gap: 1px;
	color: #00000040;
	margin-left: 2px;
}

.dt-arrow.active {
	color: #1677ff;
	font-weight: 700;
}

.dt-sort-active { color: #1677ff; }

.dt-td {
	padding: 16px 24px;
	font-size: 14px;
	color: #000000d9;
	vertical-align: middle;
	border-bottom: 1px solid #f0f0f0;
	line-height: 1.5715;
	background: #ffffff;
	transition: background-color 0.2s ease;
}

.dt-compact .dt-td {
	padding: 12px 16px;
	font-size: 14px;
}

.dt-ellipsis {
	max-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.dt-align-center { text-align: center; }
.dt-align-right { text-align: right; }

.dt-bordered .dt-td { border-right: 1px solid #f0f0f0; }
.dt-bordered .dt-th { border-right: 1px solid #f0f0f0; }
.dt-bordered .dt-th:last-child,
.dt-bordered .dt-td:last-child { border-right: none; }

.dt-zebra .dt-tr:nth-child(even) .dt-td {
	background: #ffffff;
}

.dt-tr {
	transition: background-color 0.2s ease;
	cursor: default;
}

.dt-tr:hover .dt-td {
	background: #fafafa !important;
}

.dt-sticky-header .dt-th {
	position: sticky;
	top: 0;
	z-index: 2;
}

/* ============ Checkbox ============ */
.dt-checkbox {
	width: 16px;
	height: 16px;
	accent-color: #1677ff;
	cursor: pointer;
	border-radius: 2px;
	border: 1px solid #d9d9d9;
	appearance: none;
	background: #ffffff;
	position: relative;
	vertical-align: middle;
	transition: all 0.2s ease;
}

.dt-checkbox:hover {
	border-color: #4096ff;
}

.dt-checkbox:checked {
	background: #1677ff;
	border-color: #1677ff;
}

.dt-checkbox:checked::after {
	content: '';
	position: absolute;
	left: 4px;
	top: 1px;
	width: 4px;
	height: 8px;
	border: solid #ffffff;
	border-width: 0 1.5px 1.5px 0;
	transform: rotate(45deg);
}

.dt-checkbox:indeterminate {
	background: #1677ff;
	border-color: #1677ff;
}

.dt-checkbox:indeterminate::after {
	content: '';
	position: absolute;
	left: 3px;
	top: 6px;
	width: 8px;
	height: 1.5px;
	background: #ffffff;
}

/* ============ Pagination ============ */
.dt-pagination {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	padding: 16px 24px;
	gap: 16px;
	flex-wrap: wrap;
	background: #ffffff;
}

.dt-pag-left {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	margin-right: auto;
}

.dt-pag-info {
	font-size: 14px;
	color: #000000a6;
	font-weight: 400;
	line-height: 1.5715;
}

.dt-pag-info strong {
	color: #000000d9;
	font-weight: 400;
}

.dt-pag-buttons {
	display: flex;
	align-items: center;
	gap: 8px;
}

.dt-page-btn {
	min-width: 32px;
	height: 32px;
	padding: 0 6px;
	border: 1px solid #d9d9d9;
	background: #ffffff;
	border-radius: 4px;
	font-size: 14px;
	font-weight: 400;
	color: #000000d9;
	cursor: pointer;
	transition: all 0.2s ease;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	font-family: inherit;
	line-height: 1.5715;
}

.dt-page-btn:hover:not(:disabled):not(.active) {
	color: #4096ff;
	border-color: #4096ff;
}

.dt-page-btn.active {
	background: #1677ff;
	color: #ffffff;
	border-color: #1677ff;
	font-weight: 400;
}

.dt-page-btn.active:hover {
	background: #4096ff;
	border-color: #4096ff;
}

.dt-page-btn:disabled {
	color: #00000040;
	cursor: not-allowed;
	border-color: #d9d9d9;
	background: #ffffff;
}

.dt-page-ellipsis {
	padding: 0 4px;
	color: #000000d9;
	font-size: 14px;
	line-height: 32px;
	min-width: 32px;
	text-align: center;
}

.dt-pag-right {
	display: flex;
	align-items: center;
	gap: 12px;
	flex-wrap: wrap;
}

.dt-jump {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-size: 14px;
	color: #000000a6;
	font-weight: 400;
	line-height: 1.5715;
}

.dt-jump-input {
	width: 52px;
	height: 32px;
	padding: 4px 8px;
	border: 1px solid #d9d9d9;
	background: #ffffff;
	border-radius: 4px;
	font-size: 14px;
	color: #000000d9;
	outline: none;
	text-align: center;
	transition: all 0.2s ease;
	font-family: inherit;
	line-height: 1.5715;
}

.dt-jump-input:hover {
	border-color: #4096ff;
}

.dt-jump-input:focus {
	border-color: #1677ff;
	box-shadow: 0 0 0 2px rgba(5, 145, 255, 0.1);
}

.dt-select {
	height: 32px;
	padding: 4px 24px 4px 11px;
	border: 1px solid #d9d9d9;
	background: #ffffff;
	border-radius: 4px;
	font-size: 14px;
	color: #000000d9;
	outline: none;
	cursor: pointer;
	transition: all 0.2s ease;
	font-family: inherit;
	line-height: 1.5715;
	appearance: none;
	background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2300000073' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'/%3e%3c/svg%3e");
	background-repeat: no-repeat;
	background-position: right 8px center;
	background-size: 12px;
}

.dt-select:hover {
	border-color: #4096ff;
}

.dt-select:focus {
	border-color: #1677ff;
	box-shadow: 0 0 0 2px rgba(5, 145, 255, 0.1);
}

/* ============ Empty State ============ */
.dt-empty-cell {
	padding: 0 !important;
	border-bottom: none !important;
	background: transparent !important;
}

.dt-empty {
	padding: 64px 24px 48px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 12px;
	text-align: center;
}

.dt-empty-icon {
	width: 120px;
	height: 120px;
	color: #0000002b;
	margin-bottom: 4px;
}

.dt-empty-title {
	font-size: 16px;
	font-weight: 400;
	color: #000000a6;
	line-height: 1.5715;
}

.dt-empty-desc {
	font-size: 14px;
	color: #00000073;
	max-width: 480px;
	line-height: 1.5715;
}

/* ============ Skeleton ============ */
.dt-skeleton-row .dt-td {
	border-bottom: 1px solid #f0f0f0;
}

.dt-skeleton {
	height: 16px;
	background: linear-gradient(90deg, #f2f2f2 25%, #e6e6e6 37%, #f2f2f2 63%);
	background-size: 400% 100%;
	border-radius: 2px;
	animation: dt-skeleton-loading 1.4s ease infinite;
}

.dt-skeleton-checkbox {
	width: 16px;
	height: 16px;
	border-radius: 2px;
}

@keyframes dt-skeleton-loading {
	0% {
		background-position: 100% 50%;
	}
	100% {
		background-position: 0 50%;
	}
}

/* ============ Responsive ============ */
@media (max-width: 720px) {
	.dt-toolbar {
		padding: 12px 16px;
	}
	.dt-th, .dt-td {
		padding: 12px 16px;
	}
	.dt-pagination {
		padding: 12px 16px;
		flex-direction: column;
		align-items: flex-start;
	}
	.dt-pag-left {
		margin-right: 0;
	}
	.dt-pag-buttons {
		flex-wrap: wrap;
	}
	.dt-search-input {
		width: 100%;
		max-width: 280px;
	}
}
</style>
