<script lang="ts">
import { getAdminStats } from "@api/admin";
import { isAbortedFetchError } from "@api/client";
import { onMount } from "svelte";
import BarChart from "./BarChart.svelte";
import type { Column } from "./DataTable.svelte";
import DataTable from "./DataTable.svelte";
import DonutChart from "./DonutChart.svelte";
import HeatmapCalendar from "./HeatmapCalendar.svelte";
import LineChart from "./LineChart.svelte";
import StatCard from "./StatCard.svelte";

let {
	id = undefined,
	...restProps
}: {
	id?: string;
} = $props();

/* ===================== Types ===================== */
type RangeKey = "7d" | "30d";
type StatsSummary = {
	totalPosts: number;
	totalDrafts: number;
	totalPublished: number;
	totalComments: number;
	totalPendingComments: number;
	totalUsers: number;
	totalViewsToday: number;
	totalCommentsToday: number;
};
type TopArticle = {
	id: number | string;
	title: string;
	views: number;
	comments_count: number;
};
type Commenter = {
	name: string;
	avatar: string | null;
	comments_count: number;
};
type SystemHealth = {
	cpu_percent: number | null;
	memory_percent: number | null;
	db_rtt_ms: number | null;
	cache_hit_percent: number | null;
	health_score: number | null;
};
type DashboardData = {
	summary: StatsSummary;
	timeseries: {
		labels: string[];
		datasets: { key: string; values: number[] }[];
	};
	topArticles: TopArticle[];
	activeCommenters: Commenter[];
	systemHealth: SystemHealth;
	categories?: { label: string; value: number }[];
	heatmapData?: { date: string; value: number }[];
};

/* ===================== Icon SVGs ===================== */
const ICONS = {
	posts:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14,2 14,8 20,8"/></svg>',
	drafts:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>',
	published:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
	comments:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 0 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
	pending:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
	users:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
	views:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
	commentsToday:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
	trendUp:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
	trendDown:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>',
	write:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
	post: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
	page: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
	settings:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
	edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
	delete:
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
};

/* ===================== Labels ===================== */
const L = {
	totalPosts: "文章总数",
	totalDrafts: "草稿数",
	totalPublished: "已发布",
	totalComments: "评论总数",
	pendingComments: "待审核评论",
	totalUsers: "用户总数",
	viewsToday: "今日浏览",
	commentsToday: "今日评论",
	trafficChart: "访问趋势",
	range7d: "最近 7 天",
	range30d: "最近 30 天",
	topArticles: "热门文章 Top 5",
	topArticlesSub: "按浏览量排序",
	activeCommenters: "活跃评论者 Top 5",
	activeCommentersSub: "按评论数排序",
	categoryDist: "分类占比",
	categorySub: "各分类文章数量",
	publishHeatmap: "访问热力日历",
	publishHeatmapSub: "过去 12 个月访问情况",
	monthlyPublish: "月度发文",
	monthlyPublishSub: "近 12 个月发布趋势",
	systemHealth: "系统健康",
	systemHealthSub: "CPU / 内存 / DB / 缓存",
	recentPosts: "最新文章",
	recentPostsSub: "快速管理最近内容",
	noData: "暂无数据",
	refresh: "刷新成功",
	loadError: "数据加载失败",
	welcomeTitle: "早上好，管理员 👋",
	welcomeSub: "今天是美好的一天，祝你工作愉快！",
	quickActions: "快捷操作",
	pv: "浏览量(PV)",
	uv: "访客数(UV)",
	columns: {
		title: "标题",
		category: "分类",
		views: "浏览",
		comments: "评论",
		status: "状态",
		updated: "更新时间",
		actions: "操作",
		name: "昵称",
		count: "评论数",
	},
	statusMap: {
		draft: "草稿",
		published: "已发布",
		scheduled: "定时",
		hidden: "隐藏",
	} as Record<string, string>,
	healthLabels: {
		cpu: "CPU",
		memory: "内存",
		db: "DB RTT",
		cache: "缓存命中",
		score: "健康分数",
	},
};

/* ===================== State ===================== */
let loading = $state(true);
let range = $state<RangeKey>("7d");
let data = $state<DashboardData | null>(null);
let err = $state<string | null>(null);

/* ===================== Helpers ===================== */
function pick<T>(a: T | undefined, b: T | undefined, fb: T): T {
	if (a !== undefined && a !== null) return a;
	if (b !== undefined && b !== null) return b;
	return fb;
}
function sparkFromSeries(
	datasets: { key: string; values: number[] }[],
	key: string,
): number[] {
	const ds = datasets.find((d) => d.key === key);
	return ds ? ds.values.slice(-14) : [];
}
function genSpark(n: number, base = 10): number[] {
	const arr: number[] = [];
	let v = base;
	for (let i = 0; i < n; i++) {
		v = Math.max(
			0,
			v + (Math.sin(i * 0.7) + (Math.random() - 0.5)) * base * 0.3,
		);
		arr.push(Math.round(v));
	}
	return arr;
}
function buildMockData(): DashboardData {
	const n = range === "7d" ? 7 : 30;
	const labels: string[] = [];
	const now = new Date();
	for (let i = n - 1; i >= 0; i--) {
		const d = new Date(now);
		d.setDate(d.getDate() - i);
		labels.push(`${d.getMonth() + 1}/${d.getDate()}`);
	}
	const mkSeries = (base: number) =>
		labels.map((_, i) =>
			Math.max(
				0,
				Math.round(
					base + Math.sin(i * 0.6) * base * 0.3 + Math.random() * base * 0.4,
				),
			),
		);
	return {
		summary: {
			totalPosts: 128,
			totalDrafts: 7,
			totalPublished: 118,
			totalComments: 2048,
			totalPendingComments: 12,
			totalUsers: 326,
			totalViewsToday: 1842,
			totalCommentsToday: 36,
		},
		timeseries: {
			labels,
			datasets: [
				{ key: "pv", values: mkSeries(200) },
				{ key: "uv", values: mkSeries(80) },
				{ key: "comments", values: mkSeries(20) },
				{ key: "posts", values: mkSeries(3) },
				{ key: "users", values: mkSeries(5) },
			],
		},
		topArticles: [
			{
				id: 1,
				title: "Svelte 5 Runes 模式深度实践指南",
				views: 8432,
				comments_count: 128,
			},
			{
				id: 2,
				title: "Astro SSR Streaming 性能优化全解析",
				views: 6219,
				comments_count: 94,
			},
			{
				id: 3,
				title: "前端工程化体系：从设计到工程落地",
				views: 5104,
				comments_count: 76,
			},
			{
				id: 4,
				title: "Markdown 编辑器选型对比：Vditor vs Milkdown",
				views: 4287,
				comments_count: 58,
			},
			{
				id: 5,
				title: "使用纯 SVG 构建无依赖数据可视化",
				views: 3721,
				comments_count: 41,
			},
		],
		activeCommenters: [
			{ name: "夏目贵志", avatar: null, comments_count: 86 },
			{ name: "泉こなた", avatar: null, comments_count: 64 },
			{ name: "Sakura", avatar: null, comments_count: 52 },
			{ name: "雪之下雪乃", avatar: null, comments_count: 41 },
			{ name: "御坂美琴", avatar: null, comments_count: 33 },
		],
		systemHealth: {
			cpu_percent: 38,
			memory_percent: 62,
			db_rtt_ms: 14,
			cache_hit_percent: 94,
			health_score: 92,
		},
		categories: [
			{ label: "前端技术", value: 42 },
			{ label: "后端开发", value: 28 },
			{ label: "设计笔记", value: 19 },
			{ label: "生活随笔", value: 15 },
			{ label: "工具推荐", value: 12 },
			{ label: "其他", value: 12 },
		],
		heatmapData: (() => {
			const arr: { date: string; value: number }[] = [];
			const d = new Date();
			for (let i = 0; i < 365; i++) {
				const cur = new Date(d);
				cur.setDate(cur.getDate() - i);
				const ds = cur.toISOString().slice(0, 10);
				const v = Math.random() < 0.55 ? 0 : Math.floor(Math.random() * 5) + 1;
				arr.push({ date: ds, value: v });
			}
			return arr;
		})(),
	};
}

async function load() {
	loading = true;
	err = null;
	try {
		const raw = await getAdminStats(range);
		const s: any = (raw as any).summary || {};
		const getNum = (snake: string, camel: string, fb = 0) => {
			const v = (s as any)[snake] ?? (s as any)[camel];
			return typeof v === "number" ? v : Number(v) || fb;
		};
		const summary: StatsSummary = {
			totalPosts: getNum("total_posts", "totalPosts"),
			totalDrafts: getNum("total_drafts", "totalDrafts"),
			totalPublished: getNum("total_published", "totalPublished"),
			totalComments: getNum("total_comments", "totalComments"),
			totalPendingComments: getNum(
				"total_pending_comments",
				"totalPendingComments",
			),
			totalUsers: getNum("total_users", "totalUsers"),
			totalViewsToday: getNum("total_views_today", "totalViewsToday"),
			totalCommentsToday: getNum("total_comments_today", "totalCommentsToday"),
		};
		const ts: any = (raw as any).timeseries ||
			(raw as any).timeSeries || { labels: [], datasets: [] };
		const topArticles = (
			(raw as any).top_articles ||
			(raw as any).topArticles ||
			[]
		).map((a: any) => ({
			...a,
			comments_count: a.comments_count ?? a.commentsCount ?? 0,
		}));
		const activeCommenters = (
			(raw as any).active_commenters ||
			(raw as any).activeCommenters ||
			[]
		).map((c: any) => ({
			...c,
			comments_count: c.comments_count ?? c.commentsCount ?? 0,
		}));
		const hr: any =
			(raw as any).system_health || (raw as any).systemHealth || {};
		const systemHealth: SystemHealth = {
			cpu_percent: hr.cpu_percent ?? hr.cpuPercent ?? null,
			memory_percent: hr.memory_percent ?? hr.memoryPercent ?? null,
			db_rtt_ms: hr.db_rtt_ms ?? hr.dbRttMs ?? null,
			cache_hit_percent: hr.cache_hit_percent ?? hr.cacheHitPercent ?? null,
			health_score: hr.health_score ?? hr.healthScore ?? null,
		};
		data = {
			summary,
			timeseries: ts,
			topArticles,
			activeCommenters,
			systemHealth,
			categories: (raw as any).categories,
			heatmapData: (raw as any).heatmapData || (raw as any).heatmap,
		};
		const mock = buildMockData();
		if (!data.timeseries?.labels || data.timeseries.labels.length === 0)
			data.timeseries = mock.timeseries;
		if (!data.topArticles || data.topArticles.length === 0)
			data.topArticles = mock.topArticles;
		if (!data.activeCommenters || data.activeCommenters.length === 0)
			data.activeCommenters = mock.activeCommenters;
		if (!data.categories || data.categories.length === 0)
			data.categories = mock.categories;
		if (!data.heatmapData || data.heatmapData.length === 0)
			data.heatmapData = mock.heatmapData;
		if (!data.systemHealth || data.systemHealth.health_score == null)
			data.systemHealth = mock.systemHealth;
	} catch (e: any) {
		if (isAbortedFetchError(e)) {
			// 页面导航/切换造成的请求取消：完全正常，既不告警也不降落到 mock 数据
			// （因为我们马上要被下一次 Swup content:replace 替换销毁）
			return;
		}
		console.warn("loadDashboard failed, using mock:", e);
		data = buildMockData();
	} finally {
		loading = false;
	}
}

function changeRange(r: RangeKey) {
	range = r;
	load();
}

export function refresh() {
	load();
}

/* ===================== Standalone helpers (used in {@html ...} blocks) ===================== */
function seriesLabel(key: string): string {
	const m: Record<string, string> = {
		pv: "PV",
		uv: "UV",
		comments: "评论",
		posts: "发布",
		users: "注册",
	};
	return m[key] || key;
}

function svgGauge(pct: number | null, unit = "%"): string {
	const size = 130;
	const cx = size / 2;
	const cy = size / 2;
	const r = 48;
	const strokeW = 10;
	const C = 2 * Math.PI * r;
	let color = "#52c41a";
	let value: number;
	if (pct == null || Number.isNaN(pct)) {
		value = 0;
		color = "rgba(0,0,0,0.25)";
	} else {
		value = Math.max(0, Math.min(100, pct));
		if (value >= 85) color = "#52c41a";
		else if (value >= 60) color = "#faad14";
		else color = "#ff4d4f";
	}
	const dash = C * (value / 100);
	const isDark =
		typeof document !== "undefined" &&
		document.documentElement.classList.contains("dark");
	const track = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
	const display =
		pct == null
			? "--"
			: unit === "ms"
				? `${pct.toFixed(0)} ms`
				: `${value.toFixed(value < 10 ? 1 : 0)}${unit}`;
	return `
			<svg class="gauge-wrap" viewBox="0 0 ${size} ${size}" style="width:100%;aspect-ratio:1;max-width:130px;">
				<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${track}" stroke-width="${strokeW}"/>
				<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="${strokeW}"
					stroke-dasharray="${dash} ${C}" stroke-dashoffset="${C / 4}" stroke-linecap="round"
					transform="rotate(-90 ${cx} ${cy})" style="transition: stroke-dasharray 500ms ease;"/>
				<text x="${cx}" y="${cy + 2}" text-anchor="middle" dominant-baseline="middle"
					font-size="18" font-weight="800" fill="rgba(0,0,0,0.88)" font-family="system-ui, sans-serif">${display}</text>
			</svg>`;
}

function healthScoreColor(score: number | null) {
	const s = score == null ? 80 : Math.max(0, Math.min(100, score));
	if (s >= 80)
		return {
			from: "#52c41a",
			to: "#73d13d",
			shadow: "rgba(82,196,26,0.45)",
			tag: "正常",
		};
	if (s >= 60)
		return {
			from: "#faad14",
			to: "#ffc53d",
			shadow: "rgba(250,173,20,0.45)",
			tag: "注意",
		};
	return {
		from: "#ff4d4f",
		to: "#ff7875",
		shadow: "rgba(255,77,79,0.45)",
		tag: "告警",
	};
}

function handleEdit(row: any) {
	console.log("edit", row);
}
function handleDelete(row: any) {
	console.log("delete", row);
}

onMount(() => {
	load();
});

/* ===================== Derived UI ===================== */
const pvLineData = $derived.by(() => {
	if (!data) return [];
	const pv = data.timeseries.datasets.find((d) => d.key === "pv");
	return (data.timeseries.labels || []).map((lbl, i) => ({
		label: lbl,
		value: pv?.values?.[i] ?? 0,
	}));
});
const uvLineData = $derived.by(() => {
	if (!data) return [];
	const uv = data.timeseries.datasets.find((d) => d.key === "uv");
	return (data.timeseries.labels || []).map((lbl, i) => ({
		label: lbl,
		value: uv?.values?.[i] ?? 0,
	}));
});
const pvTotal = $derived(pvLineData.reduce((a, b) => a + b.value, 0));
const uvTotal = $derived(uvLineData.reduce((a, b) => a + b.value, 0));
const lineSubtitle = $derived(range === "7d" ? L.range7d : L.range30d);

const monthlyPublishData = $derived.by(() => {
	const months: { label: string; value: number }[] = [];
	const now = new Date();
	for (let i = 11; i >= 0; i--) {
		const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
		const label = `${d.getMonth() + 1}月`;
		const value = Math.max(
			2,
			Math.round(8 + Math.sin(i * 0.8) * 5 + Math.random() * 6),
		);
		months.push({ label, value });
	}
	return months;
});

const statCards = $derived.by(() => {
	if (!data) return [];
	return [
		{
			title: "文章数",
			value: data.summary.totalPosts,
			unit: "篇",
			change: 12.5,
			iconBg: "rgba(22,119,255,0.10)",
			iconColor: "#1677ff",
			iconSvg: ICONS.posts,
		},
		{
			title: "评论数",
			value: data.summary.totalComments,
			unit: "条",
			change: 8.3,
			iconBg: "rgba(82,196,26,0.10)",
			iconColor: "#52c41a",
			iconSvg: ICONS.comments,
		},
		{
			title: "浏览量",
			value: data.summary.totalViewsToday,
			unit: "次",
			change: 15.7,
			iconBg: "rgba(250,173,20,0.10)",
			iconColor: "#faad14",
			iconSvg: ICONS.views,
		},
		{
			title: "待审核",
			value: data.summary.totalPendingComments,
			unit: "条",
			change: -3.2,
			iconBg: "rgba(255,77,79,0.10)",
			iconColor: "#ff4d4f",
			iconSvg: ICONS.pending,
		},
	];
});

const postColumns: Column<any>[] = $derived([
	{
		key: "title",
		title: L.columns.title,
		sortable: true,
		searchable: true,
		ellipsis: true,
		width: "32%",
		render: (row: any) =>
			`<a href="/admin/posts/${row.id}/" class="dt-link">${String(row.title || "无标题").replace(/</g, "&lt;")}</a>`,
	},
	{
		key: "category",
		title: L.columns.category,
		sortable: true,
		width: "12%",
		render: (row: any) =>
			`<span class="dt-tag dt-tag--soft">${String(row.category || "-").replace(/</g, "&lt;")}</span>`,
	},
	{
		key: "views",
		title: L.columns.views,
		sortable: true,
		align: "right",
		width: "10%",
		render: (row: any) =>
			`<span class="dt-num">${(row.views || 0).toLocaleString()}</span>`,
	},
	{
		key: "comments_count",
		title: L.columns.comments,
		sortable: true,
		align: "right",
		width: "10%",
		render: (row: any) =>
			`<span class="dt-num">${(row.comments_count || 0).toLocaleString()}</span>`,
	},
	{
		key: "status",
		title: L.columns.status,
		sortable: true,
		width: "12%",
		render: (row: any) => {
			const st = row.status || "published";
			const label = L.statusMap[st] || st;
			const cls =
				st === "published"
					? "dt-tag dt-tag--success"
					: st === "draft"
						? "dt-tag dt-tag--draft"
						: "dt-tag dt-tag--soft";
			return `<span class="${cls}">${label}</span>`;
		},
	},
	{
		key: "updated_at",
		title: L.columns.updated,
		sortable: true,
		width: "14%",
		align: "center",
		render: (row: any) =>
			`<span class="dt-muted">${row.updated_at || row.createdAt || "-"}</span>`,
	},
	{
		key: "actions",
		title: L.columns.actions,
		width: "10%",
		align: "center",
		render: (row: any) => `
				<div class="dt-actions">
					<button class="dt-btn dt-btn--primary" data-action="edit" data-id="${row.id}">
						${ICONS.edit}
						<span>编辑</span>
					</button>
					<button class="dt-btn dt-btn--danger" data-action="delete" data-id="${row.id}">
						${ICONS.delete}
					</button>
				</div>
			`,
	},
]);
const recentPostsTableData = $derived.by(() => {
	if (!data) return [];
	return data.topArticles.map((a, i) => ({
		...a,
		id: a.id,
		category: ["前端技术", "后端开发", "设计笔记", "生活随笔", "工具推荐"][
			i % 5
		],
		status: i % 4 === 0 ? "draft" : "published",
		updated_at: new Date(Date.now() - i * 86400000 * 2)
			.toISOString()
			.slice(0, 10),
	}));
});

const commenterColumns: Column<any>[] = $derived([
	{
		key: "name",
		title: L.columns.name,
		sortable: true,
		searchable: true,
		render: (row: any) =>
			`<div class="dt-user"><div class="dt-avatar">${initials(row.name)}</div><span>${String(row.name || "匿名").replace(/</g, "&lt;")}</span></div>`,
	},
	{
		key: "comments_count",
		title: L.columns.count,
		sortable: true,
		align: "right",
		render: (row: any) =>
			`<span class="dt-num">${(row.comments_count || 0).toLocaleString()}</span>`,
	},
]);
function initials(name: string): string {
	if (!name) return "?";
	const s = name.trim();
	if (!s) return "?";
	if (/^[\u4e00-\u9fa5]/.test(s)) return s.slice(0, 1);
	const parts = s.split(/\s+/);
	return (parts[0]?.[0] || "") + (parts[1]?.[0] || "");
}
</script>

<div {id} class="dash-panel" class:loading {...restProps}>
	{#if !loading && data}
		<!-- Row 1: 4 ProStatistic Cards -->
		<div class="stats-grid">
			{#each statCards as card, i}
				<div class="pro-stat-card">
					<div class="pro-stat-top">
						<div class="pro-stat-icon" style="background:{card.iconBg};color:{card.iconColor};">
							{@html card.iconSvg}
						</div>
						<div class="pro-stat-trend" class:down={card.change < 0}>
							{@html card.change >= 0 ? ICONS.trendUp : ICONS.trendDown}
							<span>{Math.abs(card.change).toFixed(1)}%</span>
						</div>
					</div>
					<div class="pro-stat-title">{card.title}</div>
					<div class="pro-stat-bottom">
						<span class="pro-stat-value">{card.value.toLocaleString()}</span>
						<span class="pro-stat-unit">{card.unit}</span>
					</div>
				</div>
			{/each}
		</div>

		<!-- Row 2: Welcome Banner + Quick Actions (left) & LineChart (right) -->
		<div class="row-2-grid">
			<div class="left-col">
				<!-- Welcome Banner -->
				<div class="welcome-banner">
					<div class="welcome-content">
						<div class="welcome-title">{L.welcomeTitle}</div>
						<div class="welcome-sub">{L.welcomeSub}</div>
					</div>
					<div class="welcome-decoration"></div>
				</div>

				<!-- Quick Actions -->
				<div class="quick-card">
					<div class="card-header">
						<div class="card-title">{L.quickActions}</div>
					</div>
					<div class="card-body">
						<div class="action-grid">
							<button class="action-btn action-btn--primary" onclick={() => window.location.href='/admin/posts/new/'}>
								<span class="action-icon">{@html ICONS.write}</span>
								<span class="action-label">写文章</span>
							</button>
							<button class="action-btn action-btn--success" onclick={() => console.log('post dynamic')}>
								<span class="action-icon">{@html ICONS.post}</span>
								<span class="action-label">发动态</span>
							</button>
							<button class="action-btn action-btn--warning" onclick={() => console.log('new page')}>
								<span class="action-icon">{@html ICONS.page}</span>
								<span class="action-label">建页面</span>
							</button>
							<button class="action-btn action-btn--default" onclick={() => window.location.href='/admin/settings/'}>
								<span class="action-icon">{@html ICONS.settings}</span>
								<span class="action-label">改设置</span>
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- LineChart Card -->
			<div class="chart-card">
				<div class="card-header">
					<div>
						<div class="card-title">{L.trafficChart}</div>
						<div class="card-subtitle" data-chart-subtitle>{lineSubtitle}</div>
					</div>
					<div class="chart-tabs">
						<button type="button" class:chart-tab-active={range === '7d'} class="chart-tab" onclick={() => changeRange('7d')}>{L.range7d}</button>
						<button type="button" class:chart-tab-active={range === '30d'} class="chart-tab" onclick={() => changeRange('30d')}>{L.range30d}</button>
					</div>
				</div>
				<div class="card-body">
					<div class="chart-legend-top">
						<div class="legend-item">
							<span class="legend-swatch" style="background:#1677ff"></span>
							<span class="legend-label">{L.pv}</span>
							<span class="legend-value">{pvTotal.toLocaleString()}</span>
						</div>
						<div class="legend-item">
							<span class="legend-swatch" style="background:#52c41a"></span>
							<span class="legend-label">{L.uv}</span>
							<span class="legend-value">{uvTotal.toLocaleString()}</span>
						</div>
					</div>
					<div class="dual-chart">
						<LineChart data={pvLineData} height={150} smooth={true} area={true} showDots={false} strokeWidth={2} color="#1677ff" />
						<LineChart data={uvLineData} height={110} smooth={true} area={true} showDots={false} strokeWidth={2} color="#52c41a" />
					</div>
				</div>
			</div>
		</div>

		<!-- Row 3: DonutChart + BarChart + HeatmapCalendar -->
		<div class="row-3-grid">
			<!-- DonutChart: Category Distribution -->
			<div class="card">
				<div class="card-header">
					<div>
						<div class="card-title">{L.categoryDist}</div>
						<div class="card-subtitle">{L.categorySub}</div>
					</div>
				</div>
				<div class="card-body">
					<DonutChart
						data={data.categories || []}
						size={220}
						thickness={28}
						centerLabel="文章总数"
						centerValue={data.summary.totalPosts}
						showLegend={true}
					/>
				</div>
			</div>

			<!-- BarChart: Monthly Publish -->
			<div class="card">
				<div class="card-header">
					<div>
						<div class="card-title">{L.monthlyPublish}</div>
						<div class="card-subtitle">{L.monthlyPublishSub}</div>
					</div>
				</div>
				<div class="card-body">
					<BarChart
						data={monthlyPublishData}
						height={260}
						horizontal={false}
						barRadius={4}
					/>
				</div>
			</div>

			<!-- HeatmapCalendar -->
			<div class="card">
				<div class="card-header">
					<div>
						<div class="card-title">{L.publishHeatmap}</div>
						<div class="card-subtitle">{L.publishHeatmapSub}</div>
					</div>
				</div>
				<div class="card-body">
					<HeatmapCalendar
						data={data.heatmapData || []}
						months={12}
						cellSize={11}
						cellGap={2}
					/>
				</div>
			</div>
		</div>

		<!-- Row 4: Recent Posts Table -->
		<div class="card table-card">
			<div class="card-header">
				<div>
					<div class="card-title">{L.recentPosts}</div>
					<div class="card-subtitle">{L.recentPostsSub}</div>
				</div>
				<div class="card-actions">
					<a href="/admin/posts/new/" class="btn btn-primary btn-sm">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
						新建文章
					</a>
				</div>
			</div>
			<div class="card-body p-0">
				<DataTable
					data={recentPostsTableData}
					columns={postColumns}
					rowKey="id"
					searchable={true}
					searchPlaceholder="搜索标题…"
					sortable={true}
					pagination={true}
					pageSize={8}
					pageSizeOptions={[8, 16, 32]}
					selectable={true}
					stickyHeader={true}
					compact={false}
					zebra={false}
					bordered={false}
					height={360}
					emptyTitle={L.noData}
					onRowClick={(row: any) => {
						const target = event?.target as HTMLElement;
						const actionBtn = target?.closest('[data-action]');
						if (actionBtn) {
							const action = actionBtn.getAttribute('data-action');
							if (action === 'edit') handleEdit(row);
							else if (action === 'delete') handleDelete(row);
							return;
						}
						console.log('row', row);
					}}
				/>
			</div>
		</div>
	{/if}
</div>

<style>
	.dash-panel { width: 100%; opacity: 1; transition: opacity .25s ease; }
	.dash-panel.loading { opacity: 0; }

	/* ===== Row 1: ProStatistic Cards ===== */
	.stats-grid {
		display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 16px; margin-bottom: 20px;
	}
	@media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
	@media (max-width: 640px)  { .stats-grid { grid-template-columns: 1fr; } }

	.pro-stat-card {
		background: #fff;
		border-radius: 4px;
		padding: 20px 24px;
		box-shadow: 0 1px 2px rgba(0,0,0,0.03);
	}
	.pro-stat-top {
		display: flex; align-items: flex-start; justify-content: space-between;
		margin-bottom: 12px;
	}
	.pro-stat-icon {
		width: 40px; height: 40px; border-radius: 8px;
		display: flex; align-items: center; justify-content: center;
	}
	.pro-stat-icon :global(svg) { width: 20px; height: 20px; }
	.pro-stat-trend {
		display: inline-flex; align-items: center; gap: 2px;
		font-size: 12px; font-weight: 600;
		color: #1677ff;
	}
	.pro-stat-trend.down { color: #ff4d4f; }
	.pro-stat-trend :global(svg) { width: 12px; height: 12px; }
	.pro-stat-title {
		font-size: 12px; font-weight: 400;
		color: rgba(0,0,0,0.45);
		margin-bottom: 8px;
		line-height: 1;
	}
	.pro-stat-bottom {
		display: flex; align-items: baseline; gap: 4px;
	}
	.pro-stat-value {
		font-size: 24px; font-weight: 600;
		color: rgba(0,0,0,0.88);
		line-height: 1.2;
		font-variant-numeric: tabular-nums;
		letter-spacing: -0.02em;
	}
	.pro-stat-unit {
		font-size: 14px; font-weight: 500;
		color: rgba(0,0,0,0.45);
	}

	/* ===== Row 2: Welcome + Quick Actions + LineChart ===== */
	.row-2-grid {
		display: grid; grid-template-columns: 4fr 5fr;
		gap: 20px; margin-bottom: 20px;
	}
	@media (max-width: 1200px) { .row-2-grid { grid-template-columns: 1fr; } }

	.left-col {
		display: flex; flex-direction: column; gap: 20px;
	}

	.welcome-banner {
		background: linear-gradient(135deg, #1677ff 0%, #69b1ff 100%);
		border-radius: 8px;
		padding: 24px 28px;
		position: relative;
		overflow: hidden;
		box-shadow: 0 1px 2px rgba(0,0,0,0.03);
	}
	.welcome-content {
		position: relative; z-index: 1;
	}
	.welcome-title {
		font-size: 20px; font-weight: 600;
		color: #fff;
		margin-bottom: 8px;
	}
	.welcome-sub {
		font-size: 13px;
		color: rgba(255,255,255,0.85);
	}
	.welcome-decoration {
		position: absolute; right: -40px; top: -40px;
		width: 160px; height: 160px;
		background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 70%);
		border-radius: 50%;
	}
	.welcome-decoration::after {
		content: '';
		position: absolute; right: 20px; bottom: 20px;
		width: 100px; height: 100px;
		background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
		border-radius: 50%;
	}

	.quick-card, .chart-card, .card, .table-card {
		background: #fff;
		border-radius: 8px;
		box-shadow: 0 6px 16px rgba(0,0,0,0.08);
		overflow: hidden;
	}

	.card-header {
		display: flex; align-items: center; justify-content: space-between;
		padding: 16px 24px;
		border-bottom: 1px solid #f0f0f0;
		gap: 12px;
	}
	.card-title {
		font-size: 16px; font-weight: 600;
		color: rgba(0,0,0,0.88);
		margin: 0;
		line-height: 1.4;
	}
	.card-subtitle {
		font-size: 12px;
		color: rgba(0,0,0,0.45);
		margin: 4px 0 0 0;
		font-weight: 400;
	}
	.card-body { padding: 20px 24px; }
	.card-body.p-0 { padding: 0; }
	.card-actions { display: flex; gap: 8px; }

	.action-grid {
		display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 12px;
	}
	@media (max-width: 768px) { .action-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

	.action-btn {
		display: flex; flex-direction: column; align-items: center; justify-content: center;
		gap: 8px;
		padding: 16px 8px;
		border: 1px solid #f0f0f0;
		border-radius: 6px;
		background: #fff;
		cursor: pointer;
		transition: all 0.2s ease;
		font-family: inherit;
	}
	.action-btn:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(0,0,0,0.1);
	}
	.action-icon {
		width: 36px; height: 36px;
		border-radius: 8px;
		display: flex; align-items: center; justify-content: center;
	}
	.action-icon :global(svg) { width: 18px; height: 18px; }
	.action-label {
		font-size: 13px; font-weight: 500;
		color: rgba(0,0,0,0.85);
	}
	.action-btn--primary { border-color: #bae0ff; }
	.action-btn--primary .action-icon { background: rgba(22,119,255,0.10); color: #1677ff; }
	.action-btn--primary:hover { border-color: #1677ff; }

	.action-btn--success { border-color: #b7eb8f; }
	.action-btn--success .action-icon { background: rgba(82,196,26,0.10); color: #52c41a; }
	.action-btn--success:hover { border-color: #52c41a; }

	.action-btn--warning { border-color: #ffe58f; }
	.action-btn--warning .action-icon { background: rgba(250,173,20,0.10); color: #faad14; }
	.action-btn--warning:hover { border-color: #faad14; }

	.action-btn--default { border-color: #d9d9d9; }
	.action-btn--default .action-icon { background: rgba(0,0,0,0.04); color: rgba(0,0,0,0.65); }
	.action-btn--default:hover { border-color: #1677ff; }
	.action-btn--default:hover .action-icon { background: rgba(22,119,255,0.10); color: #1677ff; }

	/* ===== Chart Styles ===== */
	.chart-tabs { display: flex; gap: 0; border: 1px solid #f0f0f0; border-radius: 4px; overflow: hidden; }
	.chart-tab {
		padding: 6px 16px; border: none; background: #fff;
		font-size: 13px; font-weight: 500;
		color: rgba(0,0,0,0.65); cursor: pointer;
		transition: all 150ms ease; font-family: inherit;
		border-right: 1px solid #f0f0f0;
	}
	.chart-tab:last-child { border-right: none; }
	.chart-tab:hover { color: #1677ff; }
	.chart-tab-active { background: #1677ff; color: #fff !important; }
	.chart-tab-active:hover { color: #fff; }

	.chart-legend-top {
		display: flex; gap: 24px; margin-bottom: 8px;
	}
	.dual-chart {
		display: flex; flex-direction: column;
	}
	.dual-chart :global(.line-chart-svg:first-child) {
		margin-bottom: 4px;
	}
	.legend-item { display: flex; align-items: center; gap: 8px; }
	.legend-swatch { width: 14px; height: 14px; border-radius: 2px; flex-shrink: 0; }
	.legend-label { font-size: 12px; color: rgba(0,0,0,0.65); font-weight: 500; }
	.legend-value { font-size: 13px; font-weight: 700; color: rgba(0,0,0,0.88); margin-left: 2px; font-variant-numeric: tabular-nums; }

	/* ===== Row 3: 3-Column Grid ===== */
	.row-3-grid {
		display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 20px; margin-bottom: 20px;
	}
	@media (max-width: 1200px) { .row-3-grid { grid-template-columns: 1fr; } }

	/* ===== Row 4: Table ===== */
	.table-card { margin-bottom: 0; }

	/* ===== Buttons ===== */
	.btn {
		display: inline-flex; align-items: center; gap: 6px;
		padding: 4px 15px;
		font-size: 14px; font-weight: 500;
		border-radius: 4px;
		border: 1px solid transparent;
		cursor: pointer;
		text-decoration: none;
		transition: all 0.2s ease;
		font-family: inherit;
		line-height: 1.5;
	}
	.btn-sm { padding: 1px 10px; font-size: 13px; }
	.btn :global(svg) { width: 14px; height: 14px; }
	.btn-primary {
		background: #1677ff;
		color: #fff;
		border-color: #1677ff;
	}
	.btn-primary:hover {
		background: #4096ff;
		border-color: #4096ff;
	}

	.p-0 { padding: 0 !important; }

	/* ===== DataTable Global Helpers ===== */
	:global(.dt-link) { color: #1677ff; text-decoration: none; font-weight: 500; }
	:global(.dt-link:hover) { color: #4096ff; text-decoration: underline; }
	:global(.dt-num) { font-variant-numeric: tabular-nums; font-weight: 600; color: rgba(0,0,0,0.88); }
	:global(.dt-muted) { color: rgba(0,0,0,0.45); font-size: 12px; }
	:global(.dt-tag) { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; line-height: 20px; border: 1px solid transparent; }
	:global(.dt-tag--soft)    { background: #fafafa; border-color: #d9d9d9; color: rgba(0,0,0,0.65); }
	:global(.dt-tag--success) { background: #f6ffed; border-color: #b7eb8f; color: #389e0d; }
	:global(.dt-tag--draft)   { background: #fffbe6; border-color: #ffe58f; color: #d48806; }
	:global(.dt-user) { display: inline-flex; align-items: center; gap: 8px; min-width: 0; }
	:global(.dt-avatar) {
		width: 28px; height: 28px; border-radius: 50%;
		background: #f5f5f5;
		display: inline-flex; align-items: center; justify-content: center;
		color: rgba(0,0,0,0.65); font-weight: 600; font-size: 12px;
		flex-shrink: 0; border: 1px solid #f0f0f0;
	}
	:global(.dt-actions) {
		display: inline-flex; align-items: center; gap: 4px;
	}
	:global(.dt-btn) {
		display: inline-flex; align-items: center; gap: 4px;
		padding: 2px 8px;
		border: 1px solid transparent;
		border-radius: 4px;
		background: transparent;
		cursor: pointer;
		font-size: 12px;
		font-family: inherit;
		transition: all 0.2s ease;
		line-height: 1.5;
	}
	:global(.dt-btn :global(svg)) { width: 12px; height: 12px; }
	:global(.dt-btn--primary) {
		color: #1677ff;
		border-color: transparent;
	}
	:global(.dt-btn--primary:hover) {
		color: #4096ff;
		background: rgba(22,119,255,0.06);
	}
	:global(.dt-btn--danger) {
		color: #ff4d4f;
		border-color: transparent;
	}
	:global(.dt-btn--danger:hover) {
		color: #ff7875;
		background: rgba(255,77,79,0.06);
	}

	/* ===== DataTable Header Style Override (AntD style) ===== */
	:global(.data-table th) {
		background: #fafafa !important;
		font-size: 14px !important;
		font-weight: 500 !important;
		color: rgba(0,0,0,0.88) !important;
		border-bottom: 2px solid #f0f0f0 !important;
	}
	:global(.data-table tbody tr:hover td) {
		background: #fafafa !important;
	}
	:global(.data-table td) {
		border-bottom: 1px solid #f0f0f0 !important;
		font-size: 13px !important;
		color: rgba(0,0,0,0.85) !important;
	}

	/* ===== System Health (if used later) ===== */
	.health-grid {
		display: grid; grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 20px;
	}
	@media (max-width: 900px) { .health-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
	@media (max-width: 560px) { .health-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
	.health-card {
		display: flex; flex-direction: column; align-items: center;
		padding: 8px 8px 16px 8px; border-radius: 8px;
		background: #fafafa;
		border: 1px solid #f0f0f0;
	}
	.health-label { font-size: 12.5px; font-weight: 600; color: rgba(0,0,0,0.45); margin-top: 8px; }
	.health-value {
		font-size: 18px; font-weight: 700; color: rgba(0,0,0,0.88);
		margin-top: 2px; font-variant-numeric: tabular-nums; letter-spacing: -0.01em;
	}
	.health-score-card {
		background: var(--hsl-from);
		color: white; border: none;
		box-shadow: 0 10px 26px -10px var(--hsl-shadow);
	}
	.health-score-card :global(.health-label),
	.health-score-card :global(.health-value) { color: white; }
	.health-score-card .health-label { opacity: 0.9; }
	.health-score-number {
		font-size: 42px; font-weight: 800;
		letter-spacing: -0.03em; line-height: 1;
		margin: 8px 0 2px 0;
	}
	.health-score-tag {
		display: inline-flex; align-items: center; gap: 6px;
		padding: 4px 12px; border-radius: 999px;
		background: rgba(255,255,255,0.22);
		font-size: 11.5px; font-weight: 700;
	}
</style>
