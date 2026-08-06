<script lang="ts">
import {
	createNavigation,
	deleteNavigation,
	getAdminNavigations,
	type Navigation,
	reorderNav,
	updateNavigation,
} from "@/api/admin";
import type {
	NavigationCreate,
	NavigationLocation,
	NavigationTreeNode,
	NavigationUpdate,
} from "@/api/schema-contract";

type LocationTab = NavigationLocation;

const LOCATION_TABS: { key: LocationTab; label: string }[] = [
	{ key: "header", label: "顶部导航" },
	{ key: "sidebar", label: "侧边导航" },
	{ key: "footer", label: "底部导航" },
];

let activeLocation: LocationTab = "header";
let flatList: Navigation[] = [];
let tree: NavigationTreeNode[] = [];
let loading = false;

interface ToastState {
	visible: boolean;
	type: "success" | "error";
	message: string;
}
let toast: ToastState = { visible: false, type: "success", message: "" };
let toastTimer: ReturnType<typeof setTimeout> | null = null;

function showToast(type: "success" | "error", message: string): void {
	if (toastTimer) clearTimeout(toastTimer);
	toast = { visible: true, type, message };
	toastTimer = setTimeout(() => {
		toast.visible = false;
	}, 3000);
}

function resolveTitle(t: unknown): string {
	if (t == null) return "";
	if (typeof t === "string") return t;
	if (typeof t === "object") {
		const obj = t as Record<string, unknown>;
		if ("zh" in obj && typeof obj.zh === "string" && obj.zh.length > 0)
			return obj.zh;
		if ("en" in obj && typeof obj.en === "string" && obj.en.length > 0)
			return obj.en;
		for (const k of Object.keys(obj)) {
			const v = (obj as Record<string, unknown>)[k];
			if (typeof v === "string" && v.length > 0) return v;
		}
	}
	return String(t);
}

function buildTree(items: Navigation[]): NavigationTreeNode[] {
	const idMap = new Map<number, NavigationTreeNode>();
	const roots: NavigationTreeNode[] = [];
	for (const item of items) {
		idMap.set(item.id, { ...item, children: [] });
	}
	const sorted = [...items].sort((a, b) => {
		if (a.order !== b.order) return a.order - b.order;
		return a.id - b.id;
	});
	for (const item of sorted) {
		const node = idMap.get(item.id) as NavigationTreeNode;
		if (item.parent_id == null) {
			roots.push(node);
		} else {
			const parent = idMap.get(item.parent_id);
			if (parent) {
				parent.children.push(node);
			} else {
				roots.push(node);
			}
		}
	}
	function sortChildren(nodes: NavigationTreeNode[]): void {
		nodes.sort((a, b) => {
			if (a.order !== b.order) return a.order - b.order;
			return a.id - b.id;
		});
		for (const n of nodes) sortChildren(n.children);
	}
	sortChildren(roots);
	return roots;
}

async function loadData(): Promise<void> {
	loading = true;
	try {
		const list = await getAdminNavigations(activeLocation);
		flatList = list as unknown as Navigation[];
		tree = buildTree(flatList as unknown as Navigation[]);
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		showToast("error", `加载失败：${msg}`);
	} finally {
		loading = false;
	}
}

function switchLocation(loc: LocationTab): void {
	activeLocation = loc;
	loadData();
}

interface DialogState {
	open: boolean;
	mode: "create" | "edit";
	editId: number | null;
	defaultParentId: number | null;
	titleZh: string;
	titleEn: string;
	url: string;
	icon: string;
	parentId: number | null;
	order: number;
	isActive: boolean;
	targetBlank: boolean;
	submitting: boolean;
}
let dialog: DialogState = {
	open: false,
	mode: "create",
	editId: null,
	defaultParentId: null,
	titleZh: "",
	titleEn: "",
	url: "",
	icon: "",
	parentId: null,
	order: 0,
	isActive: true,
	targetBlank: false,
	submitting: false,
};

function getLocationFlatList(): Navigation[] {
	return flatList.filter((n) => n.location === activeLocation);
}

function findMaxOrder(parentId: number | null): number {
	const siblings = getLocationFlatList().filter((n) =>
		parentId == null ? n.parent_id == null : n.parent_id === parentId,
	);
	if (siblings.length === 0) return 0;
	return Math.max(...siblings.map((n) => n.order)) + 1;
}

function openCreateRoot(): void {
	dialog = {
		open: true,
		mode: "create",
		editId: null,
		defaultParentId: null,
		titleZh: "",
		titleEn: "",
		url: "",
		icon: "",
		parentId: null,
		order: findMaxOrder(null),
		isActive: true,
		targetBlank: false,
		submitting: false,
	};
}

function openCreateChild(parentId: number): void {
	dialog = {
		open: true,
		mode: "create",
		editId: null,
		defaultParentId: parentId,
		titleZh: "",
		titleEn: "",
		url: "",
		icon: "",
		parentId,
		order: findMaxOrder(parentId),
		isActive: true,
		targetBlank: false,
		submitting: false,
	};
}

function openEdit(node: NavigationTreeNode): void {
	const t = node.title as unknown;
	let zh = "";
	let en = "";
	if (typeof t === "string") {
		zh = t;
	} else if (t && typeof t === "object") {
		const obj = t as Record<string, unknown>;
		if (typeof obj.zh === "string") zh = obj.zh;
		if (typeof obj.en === "string") en = obj.en;
		if (!zh) {
			for (const k of Object.keys(obj)) {
				const v = obj[k];
				if (typeof v === "string") {
					zh = v;
					break;
				}
			}
		}
	}
	dialog = {
		open: true,
		mode: "edit",
		editId: node.id,
		defaultParentId: node.parent_id,
		titleZh: zh,
		titleEn: en,
		url: node.url,
		icon: node.icon ?? "",
		parentId: node.parent_id,
		order: node.order,
		isActive: node.is_active,
		targetBlank: node.target_blank,
		submitting: false,
	};
}

function closeDialog(): void {
	dialog.open = false;
}

function collectDescendantIds(node: NavigationTreeNode): number[] {
	const ids: number[] = [];
	function walk(n: NavigationTreeNode): void {
		ids.push(n.id);
		for (const c of n.children) walk(c);
	}
	walk(node);
	return ids;
}

function findNodeById(
	nodes: NavigationTreeNode[],
	id: number,
): NavigationTreeNode | null {
	for (const n of nodes) {
		if (n.id === id) return n;
		const found = findNodeById(n.children, id);
		if (found) return found;
	}
	return null;
}

async function submitDialog(): Promise<void> {
	if (!dialog.titleZh && !dialog.titleEn) {
		showToast("error", "请至少填写中文或英文标题");
		return;
	}
	if (!dialog.url.trim()) {
		showToast("error", "请填写 URL");
		return;
	}
	dialog.submitting = true;
	try {
		const titleObj: Record<string, string> = {};
		if (dialog.titleZh.trim()) titleObj.zh = dialog.titleZh.trim();
		if (dialog.titleEn.trim()) titleObj.en = dialog.titleEn.trim();

		if (dialog.mode === "create") {
			const payload: NavigationCreate = {
				title: titleObj,
				url: dialog.url.trim(),
				icon: dialog.icon.trim() || null,
				parent_id: dialog.parentId,
				location: activeLocation,
				order: dialog.order,
				is_active: dialog.isActive,
				target_blank: dialog.targetBlank,
			};
			await createNavigation(payload);
			showToast("success", "创建成功");
		} else if (dialog.editId != null) {
			const payload: NavigationUpdate = {
				title: titleObj,
				url: dialog.url.trim(),
				icon: dialog.icon.trim() || null,
				parent_id: dialog.parentId,
				location: activeLocation,
				order: dialog.order,
				is_active: dialog.isActive,
				target_blank: dialog.targetBlank,
			};
			await updateNavigation(dialog.editId, payload);
			showToast("success", "修改成功");
		}
		closeDialog();
		await loadData();
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		showToast("error", `保存失败：${msg}`);
	} finally {
		dialog.submitting = false;
	}
}

interface DeleteDialogState {
	open: boolean;
	node: NavigationTreeNode | null;
	childCount: number;
	deleting: boolean;
}
let deleteDialog: DeleteDialogState = {
	open: false,
	node: null,
	childCount: 0,
	deleting: false,
};

function openDelete(node: NavigationTreeNode): void {
	const all = collectDescendantIds(node);
	deleteDialog = {
		open: true,
		node,
		childCount: all.length - 1,
		deleting: false,
	};
}

function closeDeleteDialog(): void {
	deleteDialog.open = false;
	deleteDialog.node = null;
}

async function confirmDelete(): Promise<void> {
	const node = deleteDialog.node;
	if (!node) return;
	deleteDialog.deleting = true;
	try {
		const originalParentId = node.parent_id;
		const childrenToPromote = [...node.children];

		await deleteNavigation(node.id);

		if (childrenToPromote.length > 0) {
			const siblingsBase = getLocationFlatList().filter((n) => {
				if (originalParentId == null)
					return n.parent_id == null && n.id !== node.id;
				return n.parent_id === originalParentId;
			});
			let nextOrder =
				siblingsBase.length > 0
					? Math.max(...siblingsBase.map((n) => n.order)) + 1
					: 0;
			for (const child of childrenToPromote) {
				await updateNavigation(child.id, {
					parent_id: originalParentId,
					order: nextOrder,
				} as NavigationUpdate);
				nextOrder += 1;
			}
		}

		showToast(
			"success",
			deleteDialog.childCount > 0
				? `删除成功，已将 ${deleteDialog.childCount} 个子节点提升至上一级`
				: "删除成功",
		);
		closeDeleteDialog();
		await loadData();
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		showToast("error", `删除失败：${msg}`);
	} finally {
		deleteDialog.deleting = false;
	}
}

function getSiblingNodes(parentId: number | null): NavigationTreeNode[] {
	if (parentId == null) return tree;
	const parent = findNodeById(tree, parentId);
	return parent ? parent.children : [];
}

async function moveUp(node: NavigationTreeNode): Promise<void> {
	const siblings = getSiblingNodes(node.parent_id);
	const idx = siblings.findIndex((n) => n.id === node.id);
	if (idx <= 0) return;
	const orderedIds = siblings.map((n) => n.id);
	const prev = orderedIds[idx - 1];
	orderedIds[idx - 1] = orderedIds[idx];
	orderedIds[idx] = prev;
	try {
		await reorderNav(orderedIds, node.parent_id, activeLocation);
		showToast("success", "已上移");
		await loadData();
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		showToast("error", `操作失败：${msg}`);
	}
}

async function moveDown(node: NavigationTreeNode): Promise<void> {
	const siblings = getSiblingNodes(node.parent_id);
	const idx = siblings.findIndex((n) => n.id === node.id);
	if (idx < 0 || idx >= siblings.length - 1) return;
	const orderedIds = siblings.map((n) => n.id);
	const next = orderedIds[idx + 1];
	orderedIds[idx + 1] = orderedIds[idx];
	orderedIds[idx] = next;
	try {
		await reorderNav(orderedIds, node.parent_id, activeLocation);
		showToast("success", "已下移");
		await loadData();
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		showToast("error", `操作失败：${msg}`);
	}
}

function buildParentOptions(): { id: number | null; label: string }[] {
	const options: { id: number | null; label: string }[] = [
		{ id: null, label: "作为根节点" },
	];
	function walk(nodes: NavigationTreeNode[], depth: number): void {
		for (const n of nodes) {
			if (dialog.mode === "edit" && dialog.editId === n.id) continue;
			const indent = "　".repeat(depth);
			options.push({
				id: n.id,
				label: `${indent}└ ${resolveTitle(n.title as unknown)}`,
			});
			walk(n.children, depth + 1);
		}
	}
	walk(tree, 0);
	return options;
}

function isFirstInLevel(node: NavigationTreeNode): boolean {
	const siblings = getSiblingNodes(node.parent_id);
	return siblings.length > 0 && siblings[0].id === node.id;
}

function isLastInLevel(node: NavigationTreeNode): boolean {
	const siblings = getSiblingNodes(node.parent_id);
	return siblings.length > 0 && siblings[siblings.length - 1].id === node.id;
}

loadData();
</script>

<div class="admin-nav-tree">
	<div class="admin-toolbar">
		<div class="toolbar-left">
			<div class="tabs">
				{#each LOCATION_TABS as tab}
					<button
						type="button"
						class="tab-btn"
						class:tab-active={activeLocation === tab.key}
						onclick={() => switchLocation(tab.key)}
						disabled={loading}
					>
						{tab.label}
					</button>
				{/each}
			</div>
		</div>
		<div class="toolbar-right">
			<button type="button" class="btn btn-outline btn-sm" onclick={loadData} disabled={loading}>
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23,4 23,10 17,10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
				刷新
			</button>
			<button type="button" class="btn btn-primary btn-sm" onclick={openCreateRoot} disabled={loading}>
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
				新增根节点
			</button>
		</div>
	</div>

	<div class="tree-container">
		{#if loading}
			<div class="empty-state">
				<div class="spinner"></div>
				<div class="empty-text">加载中...</div>
			</div>
		{:else if tree.length === 0}
			<div class="empty-state">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="empty-icon">
					<rect x="3" y="3" width="18" height="18" rx="2"/>
					<path d="M9 9h6M9 13h6M9 17h4"/>
				</svg>
				<div class="empty-title">该位置还没有导航项</div>
				<div class="empty-desc">点击右上角「+ 新增根节点」开始</div>
			</div>
		{:else}
			<div class="tree-list">
				{#each tree as node}
					{@render TreeRow({
						node,
						level: 0,
						resolveTitle,
						isFirstInLevel,
						isLastInLevel,
						onEdit: openEdit,
						onAddChild: openCreateChild,
						onDelete: openDelete,
						onMoveUp: moveUp,
						onMoveDown: moveDown,
					})}
				{/each}
			</div>
		{/if}
	</div>

	{#if dialog.open}
		<div class="modal-mask" onclick={closeDialog}>
			<div class="modal-card" onclick={(e) => e.stopPropagation()}>
				<div class="modal-header">
					<h3 class="modal-title">{dialog.mode === "create" ? "新增导航项" : "编辑导航项"}</h3>
					<button type="button" class="modal-close" onclick={closeDialog} disabled={dialog.submitting}>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
					</button>
				</div>
				<div class="modal-body">
					<div class="form-row">
						<div class="form-group">
							<label class="form-label">标题（中文）</label>
							<input
								type="text"
								class="form-input"
								bind:value={dialog.titleZh}
								placeholder="例如：首页"
								disabled={dialog.submitting}
							/>
						</div>
						<div class="form-group">
							<label class="form-label">标题（英文）</label>
							<input
								type="text"
								class="form-input"
								bind:value={dialog.titleEn}
								placeholder="e.g. Home"
								disabled={dialog.submitting}
							/>
						</div>
					</div>
					<div class="form-row">
						<div class="form-group">
							<label class="form-label">URL</label>
							<input
								type="text"
								class="form-input"
								bind:value={dialog.url}
								placeholder="/ 或 https://..."
								disabled={dialog.submitting}
							/>
						</div>
						<div class="form-group">
							<label class="form-label">图标（emoji 或文本）</label>
							<input
								type="text"
								class="form-input"
								bind:value={dialog.icon}
								placeholder="🔗 或 home"
								disabled={dialog.submitting}
							/>
						</div>
					</div>
					<div class="form-row">
						<div class="form-group">
							<label class="form-label">父节点</label>
							<select
								class="form-select"
								value={dialog.parentId == null ? "" : String(dialog.parentId)}
								onchange={(e) => {
									const v = (e.target as HTMLSelectElement).value;
									dialog.parentId = v === "" ? null : Number(v);
								}}
								disabled={dialog.submitting}
							>
								{#each buildParentOptions() as opt}
									<option value={opt.id ?? ""}>{opt.label}</option>
								{/each}
							</select>
						</div>
						<div class="form-group">
							<label class="form-label">排序（order）</label>
							<input
								type="number"
								class="form-input"
								value={dialog.order}
								oninput={(e) => {
									const v = (e.target as HTMLInputElement).value;
									dialog.order = v === "" ? 0 : Number(v);
								}}
								disabled={dialog.submitting}
							/>
						</div>
					</div>
					<div class="form-row form-row-switches">
						<label class="switch-item">
							<input type="checkbox" bind:checked={dialog.isActive} disabled={dialog.submitting} />
							<span class="switch-box"></span>
							<span class="switch-label">启用（is_active）</span>
						</label>
						<label class="switch-item">
							<input type="checkbox" bind:checked={dialog.targetBlank} disabled={dialog.submitting} />
							<span class="switch-box"></span>
							<span class="switch-label">新窗口打开（target_blank）</span>
						</label>
					</div>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-ghost btn-sm" onclick={closeDialog} disabled={dialog.submitting}>取消</button>
					<button type="button" class="btn btn-primary btn-sm" onclick={submitDialog} disabled={dialog.submitting}>
						{#if dialog.submitting}
							<span class="spinner-sm"></span>
						{/if}
						{dialog.mode === "create" ? "新增保存" : "保存修改"}
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if deleteDialog.open && deleteDialog.node}
		<div class="modal-mask" onclick={closeDeleteDialog}>
			<div class="modal-card modal-card-sm" onclick={(e) => e.stopPropagation()}>
				<div class="modal-header">
					<h3 class="modal-title">确认删除</h3>
					<button type="button" class="modal-close" onclick={closeDeleteDialog} disabled={deleteDialog.deleting}>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
					</button>
				</div>
				<div class="modal-body">
					<div class="delete-icon">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<polyline points="3,6 5,6 21,6"/>
							<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
						</svg>
					</div>
					<div class="delete-text">
						<p class="delete-main">确定要删除「<strong>{resolveTitle((deleteDialog.node as NavigationTreeNode).title as unknown)}</strong>」吗？</p>
						{#if deleteDialog.childCount > 0}
							<p class="delete-sub">该节点包含 <strong>{deleteDialog.childCount}</strong> 个子节点，删除后它们将被提到与原节点同级的父级（根级）位置，而不是一起删除。</p>
						{:else}
							<p class="delete-sub">该节点没有子节点。</p>
						{/if}
					</div>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-ghost btn-sm" onclick={closeDeleteDialog} disabled={deleteDialog.deleting}>取消</button>
					<button type="button" class="btn btn-danger btn-sm" onclick={confirmDelete} disabled={deleteDialog.deleting}>
						{#if deleteDialog.deleting}
							<span class="spinner-sm"></span>
						{/if}
						确认删除
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if toast.visible}
		<div class="toast toast-{toast.type}">
			{#if toast.type === "success"}
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="toast-icon">
					<polyline points="20,6 9,17 4,12"/>
				</svg>
			{:else}
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="toast-icon">
					<circle cx="12" cy="12" r="10"/>
					<line x1="12" y1="8" x2="12" y2="12"/>
					<line x1="12" y1="16" x2="12.01" y2="16"/>
				</svg>
			{/if}
			<span class="toast-message">{toast.message}</span>
		</div>
	{/if}
</div>

{#snippet TreeRow(p: {
	node: NavigationTreeNode;
	level: number;
	resolveTitle: (t: unknown) => string;
	isFirstInLevel: (n: NavigationTreeNode) => boolean;
	isLastInLevel: (n: NavigationTreeNode) => boolean;
	onEdit: (n: NavigationTreeNode) => void;
	onAddChild: (id: number) => void;
	onDelete: (n: NavigationTreeNode) => void;
	onMoveUp: (n: NavigationTreeNode) => void;
	onMoveDown: (n: NavigationTreeNode) => void;
})}
	<div class="tree-row" style="--level: {p.level};">
		<div class="tree-row-main">
			<span class="drag-handle" title="拖拽排序（使用上下移按钮）">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
			</span>
			<span class="nav-icon">{(p.node.icon && p.node.icon.length > 0) ? p.node.icon : "🔗"}</span>
			<span class="nav-title">{p.resolveTitle(p.node.title as unknown)}</span>
			<span class="nav-url">{p.node.url}</span>
			{#if p.node.target_blank}
				<span class="badge-accent">新窗口</span>
			{/if}
			{#if !p.node.is_active}
				<span class="badge-muted">已禁用</span>
			{/if}
			<span class="order-chip">· {p.node.order}</span>
			<span class="row-spacer"></span>
			<span class="row-actions">
				<button type="button" class="row-btn row-btn-muted" title="新增子节点" onclick={() => p.onAddChild(p.node.id)}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
					子节点
				</button>
				<button type="button" class="row-btn row-btn-blue" title="编辑" onclick={() => p.onEdit(p.node)}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
					编辑
				</button>
				<button type="button" class="row-btn row-btn-muted" title="上移" disabled={p.isFirstInLevel(p.node)} onclick={() => p.onMoveUp(p.node)}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18,15 12,9 6,15"/></svg>
				</button>
				<button type="button" class="row-btn row-btn-muted" title="下移" disabled={p.isLastInLevel(p.node)} onclick={() => p.onMoveDown(p.node)}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6,9 12,15 18,9"/></svg>
				</button>
				<button type="button" class="row-btn row-btn-red" title="删除" onclick={() => p.onDelete(p.node)}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
					删除
				</button>
			</span>
		</div>
		{#if p.node.children.length > 0}
			<div class="tree-children">
				{#each p.node.children as child}
					{@render TreeRow({
						node: child,
						level: p.level + 1,
						resolveTitle: p.resolveTitle,
						isFirstInLevel: p.isFirstInLevel,
						isLastInLevel: p.isLastInLevel,
						onEdit: p.onEdit,
						onAddChild: p.onAddChild,
						onDelete: p.onDelete,
						onMoveUp: p.onMoveUp,
						onMoveDown: p.onMoveDown,
					})}
				{/each}
			</div>
		{/if}
	</div>
{/snippet}

<style lang="css">
	.admin-nav-tree {
		background: var(--ant-bg-container);
		border: 1px solid var(--ant-border-color-secondary);
		border-radius: var(--ant-radius);
		box-shadow: var(--ant-shadow-sm);
		overflow: hidden;
	}

	.admin-toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 14px 20px;
		border-bottom: 1px solid var(--ant-border-split);
		background: var(--ant-bg-container);
		flex-wrap: wrap;
		gap: 12px;
	}

	.toolbar-left {
		display: flex;
		align-items: center;
	}

	.toolbar-right {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.tabs {
		display: flex;
		gap: 2px;
		background: var(--ant-bg-body);
		padding: 3px;
		border-radius: var(--ant-radius);
	}

	.tab-btn {
		border: none;
		background: transparent;
		padding: 6px 16px;
		font-size: 13px;
		font-weight: 500;
		color: var(--ant-text-secondary);
		border-radius: calc(var(--ant-radius) - 2px);
		cursor: pointer;
		transition: all 0.18s ease;
		font-family: inherit;
		line-height: 1.5715;
	}

	.tab-btn:hover:not(:disabled) {
		color: var(--ant-text-primary);
	}

	.tab-active {
		background: var(--ant-bg-container);
		color: var(--ant-primary);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
	}

	.tree-container {
		padding: 12px 0 16px;
		min-height: 240px;
	}

	.tree-list {
		display: flex;
		flex-direction: column;
	}

	.tree-row {
		position: relative;
	}

	.tree-row-main {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 20px 8px calc(16px + var(--level, 0) * 28px);
		border-top: 1px solid transparent;
		border-bottom: 1px solid transparent;
		transition: background 0.15s ease;
		position: relative;
	}

	.tree-row-main::before {
		content: "";
		position: absolute;
		left: calc(4px + var(--level, 0) * 28px);
		top: 0;
		bottom: 0;
		width: 1px;
		background: color-mix(in srgb, var(--ant-border-color) 55%, transparent);
	}

	.tree-row:not(.tree-row):has(> .tree-row-main) .tree-row-main::before,
	.tree-list > .tree-row > .tree-row-main::before {
		display: none;
	}

	.tree-row-main:hover {
		background: color-mix(in srgb, var(--ant-primary) 5%, transparent);
	}

	.drag-handle {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--ant-text-quaternary);
		cursor: grab;
		flex-shrink: 0;
		padding: 2px;
	}

	.drag-handle svg {
		width: 14px;
		height: 14px;
	}

	.nav-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 26px;
		height: 26px;
		min-width: 26px;
		border-radius: 6px;
		background: var(--ant-bg-body);
		font-size: 14px;
		flex-shrink: 0;
	}

	.nav-title {
		font-size: 14px;
		font-weight: 500;
		color: var(--ant-text-primary);
		flex-shrink: 0;
		line-height: 1.5715;
	}

	.nav-url {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
		font-size: 12px;
		color: var(--ant-text-tertiary);
		flex-shrink: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 220px;
	}

	.badge-accent {
		display: inline-flex;
		align-items: center;
		padding: 1px 8px;
		font-size: 11px;
		font-weight: 500;
		line-height: 1.6;
		border-radius: 9999px;
		background: color-mix(in srgb, var(--indigo-500) 14%, transparent);
		color: var(--indigo-600);
		flex-shrink: 0;
	}

	html.dark .badge-accent {
		background: color-mix(in srgb, var(--indigo-400) 18%, transparent);
		color: var(--indigo-300);
	}

	.badge-muted {
		display: inline-flex;
		align-items: center;
		padding: 1px 8px;
		font-size: 11px;
		font-weight: 500;
		line-height: 1.6;
		border-radius: 9999px;
		background: var(--ant-bg-body);
		color: var(--ant-text-tertiary);
		border: 1px solid var(--ant-border-color-secondary);
		flex-shrink: 0;
	}

	.order-chip {
		font-size: 12px;
		color: var(--ant-text-quaternary);
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		flex-shrink: 0;
	}

	.row-spacer {
		flex: 1;
		min-width: 8px;
	}

	.row-actions {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
	}

	.row-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 3px;
		padding: 3px 8px;
		height: 24px;
		border: 1px solid transparent;
		border-radius: var(--ant-radius-sm);
		background: transparent;
		cursor: pointer;
		font-size: 12px;
		font-weight: 450;
		line-height: 1;
		transition: all 0.15s ease;
		font-family: inherit;
		color: var(--ant-text-secondary);
	}

	.row-btn svg {
		width: 12px;
		height: 12px;
		flex-shrink: 0;
	}

	.row-btn:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.row-btn-muted {
		color: var(--ant-text-secondary);
	}
	.row-btn-muted:hover:not(:disabled) {
		background: var(--ant-bg-body);
		border-color: var(--ant-border-color);
		color: var(--ant-text-primary);
	}

	.row-btn-blue {
		color: var(--ant-primary);
	}
	.row-btn-blue:hover:not(:disabled) {
		background: var(--ant-primary-bg);
		border-color: color-mix(in srgb, var(--ant-primary) 35%, transparent);
	}

	.row-btn-red {
		color: #ff4d4f;
	}
	.row-btn-red:hover:not(:disabled) {
		background: #fff2f0;
		border-color: #ffccc7;
	}
	html.dark .row-btn-red:hover:not(:disabled) {
		background: rgba(255, 77, 79, 0.1);
		border-color: rgba(255, 77, 79, 0.3);
	}

	.tree-children {
		display: flex;
		flex-direction: column;
	}

	.tree-children > :global(.tree-row) {
		/* handled via inline style padding */
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 72px 24px;
		gap: 12px;
		color: var(--ant-text-tertiary);
	}

	.empty-icon {
		width: 44px;
		height: 44px;
		opacity: 0.45;
	}

	.empty-title {
		font-size: 15px;
		font-weight: 500;
		color: var(--ant-text-secondary);
	}

	.empty-desc {
		font-size: 13px;
		color: var(--ant-text-tertiary);
	}

	.empty-text {
		font-size: 13px;
	}

	.spinner {
		width: 28px;
		height: 28px;
		border: 2.5px solid var(--ant-border-color);
		border-top-color: var(--ant-primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.spinner-sm {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.45);
		border-top-color: #fff;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
		margin-right: 6px;
		vertical-align: -2px;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.modal-mask {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		backdrop-filter: blur(2px);
		animation: maskIn 0.18s ease-out;
		padding: 24px;
	}

	@keyframes maskIn {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	.modal-card {
		background: var(--ant-bg-container);
		border-radius: var(--ant-radius-lg);
		width: 100%;
		max-width: 640px;
		box-shadow: 0 12px 48px rgba(0, 0, 0, 0.22);
		animation: cardIn 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		max-height: calc(100vh - 48px);
	}

	.modal-card-sm {
		max-width: 480px;
	}

	@keyframes cardIn {
		from {
			opacity: 0;
			transform: translateY(14px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid var(--ant-border-split);
		flex-shrink: 0;
	}

	.modal-title {
		margin: 0;
		font-size: 16px;
		font-weight: 600;
		color: var(--ant-text-primary);
		letter-spacing: -0.005em;
		line-height: 1.4;
	}

	.modal-close {
		width: 30px;
		height: 30px;
		border: none;
		background: transparent;
		color: var(--ant-text-tertiary);
		cursor: pointer;
		border-radius: var(--ant-radius-sm);
		display: inline-flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
		flex-shrink: 0;
	}
	.modal-close svg { width: 16px; height: 16px; }
	.modal-close:hover:not(:disabled) {
		background: var(--ant-bg-body);
		color: var(--ant-text-primary);
	}

	.modal-body {
		padding: 20px;
		overflow-y: auto;
		flex: 1;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 14px;
		margin-bottom: 16px;
	}

	.form-row-switches {
		display: flex;
		flex-wrap: wrap;
		gap: 20px;
		grid-template-columns: none;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.form-label {
		font-size: 13px;
		font-weight: 500;
		color: var(--ant-text-secondary);
		line-height: 1.4;
	}

	.form-input,
	.form-select {
		width: 100%;
		height: 34px;
		padding: 4px 11px;
		font-size: 14px;
		line-height: 1.5715;
		color: var(--ant-text-primary);
		background: var(--ant-bg-container);
		border: 1px solid var(--ant-border-color);
		border-radius: var(--ant-radius-sm);
		outline: none;
		transition: all 0.18s ease;
		font-family: inherit;
		box-sizing: border-box;
	}

	.form-input::placeholder {
		color: var(--ant-text-quaternary);
	}

	.form-input:focus,
	.form-select:focus {
		border-color: var(--ant-primary);
		box-shadow: 0 0 0 2px var(--ant-primary-bg);
	}

	.form-input:disabled,
	.form-select:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		background: var(--ant-bg-body);
	}

	.switch-item {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		cursor: pointer;
		user-select: none;
		font-size: 13px;
		color: var(--ant-text-primary);
	}

	.switch-item input[type="checkbox"] {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}

	.switch-box {
		position: relative;
		width: 36px;
		height: 20px;
		background: var(--ant-border-color);
		border-radius: 9999px;
		transition: background 0.18s ease;
		flex-shrink: 0;
	}
	.switch-box::after {
		content: "";
		position: absolute;
		top: 2px;
		left: 2px;
		width: 16px;
		height: 16px;
		background: #fff;
		border-radius: 50%;
		transition: transform 0.18s ease;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
	}

	.switch-item input[type="checkbox"]:checked + .switch-box {
		background: var(--ant-primary);
	}
	.switch-item input[type="checkbox"]:checked + .switch-box::after {
		transform: translateX(16px);
	}

	.switch-label {
		line-height: 1.4;
	}

	.modal-footer {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 8px;
		padding: 12px 20px;
		border-top: 1px solid var(--ant-border-split);
		background: color-mix(in srgb, var(--ant-bg-body) 55%, transparent);
		flex-shrink: 0;
	}

	.delete-icon {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: #fff2f0;
		color: #ff4d4f;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		margin: 0 auto 16px;
	}
	html.dark .delete-icon {
		background: rgba(255, 77, 79, 0.12);
		color: #ff7875;
	}
	.delete-icon svg {
		width: 24px;
		height: 24px;
	}

	.delete-text {
		text-align: center;
	}
	.delete-main {
		margin: 0 0 8px;
		font-size: 14px;
		color: var(--ant-text-primary);
		line-height: 1.6;
	}
	.delete-sub {
		margin: 0;
		font-size: 13px;
		color: var(--ant-text-secondary);
		line-height: 1.6;
	}
	.delete-sub strong {
		color: var(--admin-warn);
	}

	.toast {
		position: fixed;
		top: 24px;
		left: 50%;
		transform: translateX(-50%);
		z-index: 2000;
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 10px 16px;
		border-radius: var(--ant-radius);
		box-shadow: 0 6px 24px rgba(0, 0, 0, 0.14);
		font-size: 14px;
		line-height: 1.4;
		animation: toastIn 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
		max-width: calc(100vw - 48px);
	}

	@keyframes toastIn {
		from {
			opacity: 0;
			transform: translate(-50%, -12px);
		}
		to {
			opacity: 1;
			transform: translate(-50%, 0);
		}
	}

	.toast-success {
		background: #f6ffed;
		border: 1px solid #b7eb8f;
		color: #389e0d;
	}
	html.dark .toast-success {
		background: rgba(56, 158, 13, 0.14);
		border-color: rgba(82, 196, 26, 0.35);
		color: #95de64;
	}

	.toast-error {
		background: #fff2f0;
		border: 1px solid #ffccc7;
		color: #cf1322;
	}
	html.dark .toast-error {
		background: rgba(207, 19, 34, 0.13);
		border-color: rgba(255, 77, 79, 0.35);
		color: #ff7875;
	}

	.toast-icon {
		width: 18px;
		height: 18px;
		flex-shrink: 0;
	}

	.toast-message {
		word-break: break-all;
	}

	@media (max-width: 720px) {
		.form-row {
			grid-template-columns: 1fr;
		}
		.nav-url {
			display: none;
		}
	}
</style>
