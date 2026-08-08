/**
 * OOBE Wizard Composable
 *
 * 提取 OobeWizard.svelte 的所有状态管理和业务逻辑到可复用的 composable。
 * 使用 Svelte 5 runes ($state) 实现响应式。
 */
import { apiGet, apiPost } from "@/api/client";
import type {
	DatabaseType,
	EnvCheckItem,
	InstallResult,
	InstallStep,
	OobeDraft,
	StepStatus,
	ThemeMode,
} from "@/types/oobe";
import {
	OOBE_FEATURE_DEFAULTS,
	OOBE_FEATURE_FLAGS,
	OOBE_FEATURE_META,
} from "@/types/oobe";
import { playThemeReveal } from "@/utils/setting-utils";

// ===== Re-export from types =====
export const FEATURE_LABELS: Record<string, string> = OOBE_FEATURE_FLAGS;
export const FEATURE_META: Record<string, { icon: string; desc: string }> =
	OOBE_FEATURE_META;

// ===== Constants =====
export const DRAFT_KEY = "rosetta-oobe-draft-v1";
export const THEME_STORAGE_KEY = "theme";
export const LANG_STORAGE_KEY = "lang";
export const HUE_STORAGE_KEY = "hue";
export const DEFAULT_HUE = 250;

export const OOBE_LANGS: Array<{ code: string; label: string; short: string }> =
	[
		{ code: "zh_CN", label: "简体中文", short: "简中" },
		{ code: "zh_TW", label: "繁體中文", short: "繁中" },
		{ code: "en", label: "English", short: "EN" },
		{ code: "ja", label: "日本語", short: "日本語" },
	];

export const STEPS = [
	"欢迎",
	"环境检测",
	"数据库",
	"站点与管理员",
	"功能开关",
	"完成",
];

export const WELCOME_FEATURES: Array<{
	icon: string;
	title: string;
	desc: string;
}> = [
	{
		icon: "material-symbols:edit-note-rounded",
		title: "Markdown 全插件",
		desc: "内置 KaTeX / Mermaid / PlantUML / 代码分组",
	},
	{
		icon: "material-symbols:translate-rounded",
		title: "多语言 i18n",
		desc: "简体 / 繁体 / English / 日本語",
	},
	{
		icon: "material-symbols:mode-comment-outline-rounded",
		title: "评论审核",
		desc: "内置 Twikoo / Waline / Giscus / Disqus 支持",
	},
	{
		icon: "material-symbols:image-rounded",
		title: "Bing 每日壁纸",
		desc: "每日自动更新首页 Banner 桌面/手机壁纸",
	},
	{
		icon: "material-symbols:shield-lock-outline-rounded",
		title: "生产安全",
		desc: "HTTPS 加固、CSP、注入防护、权限分级",
	},
	{
		icon: "material-symbols:rocket-launch-rounded",
		title: "一键安装",
		desc: "SQLite 0 配置启动，Postgres 一行切换",
	},
];

export type DepItem = {
	name: string;
	label: string;
	required: boolean;
	installed: boolean;
	version?: string;
	required_version?: string;
	detail?: string;
};

// ===== Class-based reactive state (Svelte 5 runes) =====
class OobeWizardState {
	currentStep = $state(1);
	stepVisible = $state(true);
	animDir = $state<"next" | "prev">("next");
	toast = $state<{ type: "success" | "error" | "info"; msg: string } | null>(
		null,
	);
	envChecks = $state<EnvCheckItem[]>([]);
	envLoading = $state(false);
	installing = $state(false);
	installProgress = $state(0);
	installSteps = $state<InstallStep[]>([]);
	installError = $state<string | null>(null);
	installResult = $state<InstallResult | null>(null);
	showErrorDetail = $state<Record<number, boolean>>({});

	// ===== Backend connectivity =====
	backendReachable = $state<"unknown" | "yes" | "no">("unknown");
	backendCheckLoading = $state(false);
	backendLastError = $state<string | null>(null);

	// ===== Dependencies (OOBE install step + env step both use) =====
	deps = $state<DepItem[]>([]);
	depsLoading = $state(false);
	depsInstalling = $state(false);
	depsInstallLog = $state<string[]>([]);
	depsInstallProgress = $state(0);
	depsInstallError = $state<string | null>(null);

	draft = $state<OobeDraft>({
		database: {
			dbType: "sqlite" as DatabaseType,
			dbHost: "localhost",
			dbPort: 5432,
			dbName: "rosetta",
			dbUser: "postgres",
			dbPassword: "",
			redisEnable: false,
			redisHost: "localhost",
			redisPort: 6379,
			redisPassword: "",
		},
		site: {
			siteName: "Rosetta",
			siteUrl: "https://rosetta.choyeon.cc",
			siteDescription: "一个功能齐全、主题优雅、开箱即用的现代博客引擎",
			siteKeywords: "Rosetta,博客,技术,全栈",
			siteAuthor: "Choyeon",
			siteEmail: "choyeon@foxmail.com",
		},
		admin: {
			adminUsername: "Choyeon",
			adminEmail: "choyeon@foxmail.com",
			adminNickname: "Choyeon",
			adminPassword: "Choyeon@2025",
			confirmAdminPassword: "Choyeon@2025",
		},
		features: { ...OOBE_FEATURE_DEFAULTS },
	});

	errors = $state<Record<string, string>>({});

	themeMode = $state<ThemeMode>("light");
	currentTheme = $state<"light" | "dark">("light");
	currentLang = $state<string>("zh_CN");
	langPanelOpen = $state(false);

	// ===== Toast & Draft =====
	showToast(type: "success" | "error" | "info", msg: string) {
		this.toast = { type, msg };
		setTimeout(() => {
			this.toast = null;
		}, 3000);
	}

	saveDraft() {
		const safe = {
			...this.draft,
			site: { ...(this.draft.site ?? {}) },
			admin: {
				...(this.draft.admin ?? {}),
				adminPassword: "",
				confirmAdminPassword: "",
			},
			database: { ...(this.draft.database ?? {}) },
			features: { ...(this.draft.features ?? {}) },
		};
		try {
			localStorage.setItem(DRAFT_KEY, JSON.stringify(safe));
		} catch {
			/* ignore */
		}
	}

	loadDraft() {
		try {
			const s = localStorage.getItem(DRAFT_KEY);
			if (s) {
				const parsed = JSON.parse(s) as Partial<OobeDraft>;
				// 深合并，避免浅 spread 把整段 site/admin/database 覆盖掉导致默认字段全部 undefined
				const merged: OobeDraft = {
					...this.draft,
					database: {
						...this.draft.database,
						...(parsed.database ?? {}),
					},
					site: {
						...this.draft.site,
						...(parsed.site ?? {}),
					},
					admin: {
						...this.draft.admin,
						...(parsed.admin ?? {}),
						adminPassword: "",
						confirmAdminPassword: "",
					},
					features: { ...OOBE_FEATURE_DEFAULTS, ...(parsed.features ?? {}) },
				};
				// 字符串字段强制归一，避免 null/undefined 残留
				for (const k of Object.keys(
					merged.site,
				) as (keyof OobeDraft["site"])[]) {
					const v: any = (merged.site as any)[k];
					if (typeof v !== "string") (merged.site as any)[k] = "";
				}
				for (const k of Object.keys(
					merged.admin,
				) as (keyof OobeDraft["admin"])[]) {
					const v: any = (merged.admin as any)[k];
					if (typeof v !== "string") (merged.admin as any)[k] = "";
				}
				this.draft = merged;
			}
		} catch {
			/* ignore */
		}
	}

	// ===== Backend connectivity probe =====
	async checkBackendConnectivity(force = false): Promise<boolean> {
		// 若已有一次探活正在进行：直接返回当前状态，不再起新请求也不空转等。
		// 原因：UI 通过 $state 响应式更新，等当前探活 finally 结束后，
		// backendReachable/backendCheckLoading 会自动触发重渲染，按钮/离线页会自行刷新。
		if (this.backendCheckLoading && !force) {
			return this.backendReachable === "yes";
		}
		this.backendCheckLoading = true;
		this.backendLastError = null;
		// 保险：即使 fetch/AbortController 有极端情况卡死（某些浏览器/代理组合），
		// 最多 6 秒后强制释放 backendCheckLoading 锁，避免按钮永远"检测后端中…"卡死。
		// （_timeout=4000ms，再加 2000ms 余量。）
		const guardTimer = setTimeout(() => {
			if (this.backendCheckLoading) {
				this.backendReachable = this.backendReachable === "yes" ? "yes" : "no";
				if (this.backendReachable !== "yes") {
					this.backendLastError = this.backendLastError || "后端响应超时";
				}
				this.backendCheckLoading = false;
			}
		}, 6000);
		try {
			const data = await apiGet<any>("/oobe/status", { _timeout: 4000 });
			void data;
			this.backendReachable = "yes";
			return true;
		} catch (e: any) {
			this.backendReachable = "no";
			const code = e?.code || "";
			const msg = e?.message || "网络错误";
			let reason = msg;
			if (
				typeof msg === "string" &&
				/(Failed to fetch|NetworkError|fetch failed|ENOTFOUND|ECONNREFUSED|timeout|timed out)/i.test(
					msg,
				)
			) {
				reason = "连接不到后端服务器";
			} else if (
				code === "ERR_ABORTED" ||
				code === 502 ||
				code === 503 ||
				code === 504
			) {
				reason = "后端服务未启动或暂时不可用";
			}
			this.backendLastError = reason;
			return false;
		} finally {
			clearTimeout(guardTimer);
			this.backendCheckLoading = false;
		}
	}

	// ===== Dependencies =====
	async loadDeps(force = false) {
		if (this.depsLoading && !force) return;
		this.depsLoading = true;
		try {
			// 后端 /api/oobe/dependencies 返回：
			//   { success: true, python: {available,version,required,message}, uv: {...}, node: {...},
			//     pnpm: {...}, postgresql: {...}, redis: {...}, npm: {...}, pip: {...}, sqlite: {...} }
			const r = await apiGet<any>("/oobe/dependencies", { _timeout: 6000 });
			const payload = r && typeof r === "object" ? r : {};
			const map: Record<string, { label: string; required: boolean }> = {
				python: { label: "Python", required: true },
				uv: { label: "uv", required: true },
				node: { label: "Node.js", required: true },
				pnpm: { label: "pnpm", required: true },
				npm: { label: "npm", required: false },
				pip: { label: "pip", required: false },
				postgresql: { label: "PostgreSQL", required: false },
				redis: { label: "Redis", required: false },
				sqlite: { label: "SQLite", required: false },
			};
			const out: DepItem[] = [];
			for (const key of Object.keys(map)) {
				const raw: any = (payload as any)[key];
				if (!raw || typeof raw !== "object") continue;
				const available = !!raw.available;
				const version = typeof raw.version === "string" ? raw.version : "";
				const requiredVersion =
					typeof raw.required === "string" ? raw.required : "";
				const message =
					typeof raw.message === "string"
						? raw.message
						: available
							? "已安装"
							: "未检测到";
				out.push({
					name: key,
					label: map[key].label,
					required: map[key].required,
					installed: available,
					version,
					required_version: requiredVersion,
					detail: message,
				});
			}
			// 若后端未返回 map 中任意一项，说明 API 返回结构有变化 —— 给至少一个可见的占位，避免 UI 空无一物
			if (out.length === 0) {
				const hint =
					payload && typeof payload === "object"
						? Object.keys(payload as any).join(", ")
						: "";
				out.push({
					name: "unknown",
					label: "依赖探测",
					required: false,
					installed: false,
					detail: hint ? `后端返回字段：${hint}` : "未读取到依赖信息",
				});
			}
			this.deps = out;
		} catch (e: any) {
			this.deps = [];
			if (this.backendReachable === "unknown") {
				void this.checkBackendConnectivity(true);
			}
			this.showToast("error", e?.message || "读取依赖列表失败");
		} finally {
			this.depsLoading = false;
		}
	}

	async installDeps(): Promise<boolean> {
		if (this.depsInstalling) return false;
		this.depsInstalling = true;
		this.depsInstallProgress = 0;
		this.depsInstallError = null;
		this.depsInstallLog = ["开始安装运行时依赖…"];
		const pushLog = (line: string) => {
			this.depsInstallLog = [...this.depsInstallLog, line].slice(-120);
		};
		try {
			const ticker = setInterval(() => {
				this.depsInstallProgress = Math.min(95, this.depsInstallProgress + 3);
				pushLog(`… 仍在处理 (${this.depsInstallProgress}%)`);
			}, 1200);
			const r = await apiPost<any>(
				"/oobe/install-dependencies",
				{},
				{ _timeout: 10 * 60 * 1000 },
			);
			clearInterval(ticker);
			this.depsInstallProgress = 100;
			const ok =
				r?.success === true ||
				r?.data?.success === true ||
				r?.installed === true;
			const logs: string[] = r?.data?.logs ?? r?.logs ?? [];
			if (Array.isArray(logs)) {
				for (const L of logs) pushLog(String(L));
			}
			if (ok) {
				pushLog("✔ 依赖安装完成");
				void this.loadDeps(true);
				this.showToast("success", "依赖安装完成");
				return true;
			}
			const msg = r?.data?.message ?? r?.message ?? "依赖安装失败";
			this.depsInstallError = msg;
			pushLog(`✖ ${msg}`);
			this.showToast("error", msg);
			return false;
		} catch (e: any) {
			this.depsInstallError = e?.message || "依赖安装失败";
			pushLog(`✖ ${this.depsInstallError}`);
			this.showToast("error", this.depsInstallError || "依赖安装失败");
			return false;
		} finally {
			this.depsInstalling = false;
		}
	}

	// ===== Step Navigation =====
	goStep(step: number) {
		if (step < 1 || step > STEPS.length) return;
		if (step > this.currentStep + 1) return;
		this.animDir = step > this.currentStep ? "next" : "prev";
		this.stepVisible = false;
		try {
			this.saveDraft();
		} catch {
			/* ignore */
		}
		setTimeout(() => {
			this.currentStep = step;
			this.stepVisible = true;
			// 注意：Step 2 的 env-check 只在首次进入、列表为空时才自动执行（避免用户回到 Step2 每次都重跑）
			if (step === 2 && this.envChecks.length === 0) void this.runEnvCheck();
			// Step 6 的安装不再在 goStep 里触发：Step 5 按钮 click 里显式调用 startInstall()，保证用户点了就一定能触发。
			// 但在刷新页面导致 draft/URL 直接落在 Step 6 的情况下仍需兜底。
			if (
				step === 6 &&
				!this.installResult &&
				!this.installing &&
				!this.installStartLock
			)
				void this.startInstall();
		}, 220);
	}

	next() {
		if (this.currentStep === 1) {
			this.goStep(2);
			return;
		}
		if (this.currentStep === 2) {
			this.goStep(3);
			return;
		}
		if (this.currentStep === 3) {
			if (this.validateDatabase()) this.goStep(4);
			return;
		}
		if (this.currentStep === 4) {
			if (this.validateSiteAdmin()) this.goStep(5);
			return;
		}
		if (this.currentStep === 5) {
			this.goStep(6);
			return;
		}
	}

	back() {
		if (this.currentStep > 1) this.goStep(this.currentStep - 1);
	}

	// ===== Env Check =====
	async runEnvCheck() {
		this.envLoading = true;
		this.envChecks = [];
		// 先探活后端，把"后端连接"作为第 0 项检查
		const reachable = await this.checkBackendConnectivity(true);
		// 顺便加载依赖列表（即使失败也不影响环境检测继续）
		void this.loadDeps(true).catch(() => {
			/* ignore */
		});
		try {
			await apiPost("/oobe/reset", {}).catch(() => {
				/* ignore */
			});
		} catch {
			/* ignore */
		}
		try {
			const data = await apiGet<any>("/oobe/check", { _timeout: 8000 });
			const list = data?.data?.checks || data?.checks || [];
			const envList: EnvCheckItem[] =
				Array.isArray(list) && list.length > 0
					? list
					: this.fallbackEnvChecks(data);
			// 插入"后端连接"项，保证用户最关心的状态最先显示
			const backendCheck: EnvCheckItem = reachable
				? {
						name: "后端服务器连接",
						status: "pass",
						value: "已连接",
						detail: "OOBE API 正常响应",
					}
				: {
						name: "后端服务器连接",
						status: "fail",
						value: this.backendLastError || "未连接",
						detail: "请确认后端服务已启动并监听正确端口",
					};
			this.envChecks = [backendCheck, ...envList];
		} catch (e: any) {
			const fallback = this.fallbackEnvChecks(null);
			const backendCheck: EnvCheckItem = reachable
				? {
						name: "后端服务器连接",
						status: "pass",
						value: "已连接",
						detail: "OOBE API 正常响应",
					}
				: {
						name: "后端服务器连接",
						status: "fail",
						value: this.backendLastError || "未连接",
						detail: "请确认后端服务已启动并监听正确端口",
					};
			this.envChecks = [backendCheck, ...fallback];
			if (!reachable) {
				// 已在 backendCheck 里展示，就不再额外 toast 打扰用户
			} else {
				this.showToast("error", e?.message || "环境检测失败");
			}
		} finally {
			this.envLoading = false;
		}
	}

	fallbackEnvChecks(data: any): EnvCheckItem[] {
		return [
			{
				name: "Node.js 版本",
				status: "info",
				value: "≥ 18",
				detail: "检测到环境，若安装失败请手动确认版本",
			},
			{
				name: "数据库依赖",
				status: data?.database ? "pass" : "info",
				value: data?.database ? "OK" : "待配置",
				detail: "SQLite 0 配置，PostgreSQL 需要预先创建数据库",
			},
			{
				name: "磁盘空间",
				status: "info",
				value: "≥ 500MB",
				detail: "建议至少 1GB 可用空间",
			},
			{
				name: "文件写入权限",
				status: "info",
				value: "待检测",
				detail: "安装过程会自动验证目录可写性",
			},
			{
				name: "网络连通性",
				status: "info",
				value: "N/A",
				detail: "部分功能（Bing 壁纸、追番等）需要外网访问",
			},
			{
				name: "内存",
				status: "info",
				value: "≥ 512MB",
				detail: "生产环境建议 ≥ 1GB",
			},
			{
				name: "浏览器兼容",
				status: "pass",
				value: "通过",
				detail: "支持现代浏览器（Chrome/Edge/Firefox/Safari 最新两版）",
			},
			{
				name: "依赖完整度",
				status: "info",
				value: "待安装",
				detail: "点击「下一步」配置数据库并安装依赖",
			},
		];
	}

	// ===== Validation =====
	validateDatabase(): boolean {
		this.errors = {};
		if (this.draft.database.dbType === "postgres") {
			if (!(this.draft.database.dbHost ?? "").trim())
				this.errors.dbHost = "请输入数据库主机";
			if (
				this.draft.database.dbPort == null ||
				String(this.draft.database.dbPort).trim() === ""
			)
				this.errors.dbPort = "请输入端口";
			if (!(this.draft.database.dbName ?? "").trim())
				this.errors.dbName = "请输入数据库名";
			if (!(this.draft.database.dbUser ?? "").trim())
				this.errors.dbUser = "请输入用户名";
		}
		return Object.keys(this.errors).length === 0;
	}

	validateSiteAdmin(): boolean {
		this.errors = {};
		const siteName = this.draft.site?.siteName ?? "";
		if (!siteName.trim()) this.errors.siteName = "请输入站点名称";
		const userRe = /^[A-Za-z0-9_-]{3,20}$/;
		const adminUsername = this.draft.admin?.adminUsername ?? "";
		const adminEmail = this.draft.admin?.adminEmail ?? "";
		const adminPassword = this.draft.admin?.adminPassword ?? "";
		const confirmAdminPassword = this.draft.admin?.confirmAdminPassword ?? "";
		if (!userRe.test(adminUsername))
			this.errors.adminUsername = "用户名为 3-20 位字母、数字、下划线或短横线";
		if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminEmail))
			this.errors.adminEmail = "请输入有效邮箱";
		if (adminPassword.length < 8) this.errors.adminPassword = "密码至少 8 位";
		if (adminPassword !== confirmAdminPassword)
			this.errors.confirmAdminPassword = "两次输入的密码不一致";
		return Object.keys(this.errors).length === 0;
	}

	validateAdminUsername() {
		const userRe = /^[A-Za-z0-9_-]{3,20}$/;
		const adminUsername = this.draft.admin?.adminUsername ?? "";
		if (!userRe.test(adminUsername))
			this.errors = {
				...this.errors,
				adminUsername: "用户名为 3-20 位字母、数字、下划线或短横线",
			};
		else {
			const n = { ...this.errors };
			delete n.adminUsername;
			this.errors = n;
		}
	}

	validateAdminEmail() {
		const adminEmail = this.draft.admin?.adminEmail ?? "";
		if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminEmail))
			this.errors = { ...this.errors, adminEmail: "请输入有效邮箱" };
		else {
			const n = { ...this.errors };
			delete n.adminEmail;
			this.errors = n;
		}
	}

	validateAdminPwd() {
		const adminPassword = this.draft.admin?.adminPassword ?? "";
		if (adminPassword.length < 8)
			this.errors = { ...this.errors, adminPassword: "密码至少 8 位" };
		else {
			const n = { ...this.errors };
			delete n.adminPassword;
			this.errors = n;
		}
	}

	validateAdminConfirm() {
		const adminPassword = this.draft.admin?.adminPassword ?? "";
		const confirmAdminPassword = this.draft.admin?.confirmAdminPassword ?? "";
		if (adminPassword !== confirmAdminPassword)
			this.errors = {
				...this.errors,
				confirmAdminPassword: "两次输入的密码不一致",
			};
		else {
			const n = { ...this.errors };
			delete n.confirmAdminPassword;
			this.errors = n;
		}
	}

	// ===== Install =====
	private uuidv4(): string {
		if (crypto.randomUUID) return crypto.randomUUID();
		return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
			const r = (Math.random() * 16) | 0;
			const v = c === "x" ? r : (r & 0x3) | 0x8;
			return v.toString(16);
		});
	}

	private installStartLock = false;

	async startInstall(): Promise<boolean> {
		// 防重入：用户在 Step5 重复点多次 / Step 6 内点重试都不重复跑
		if (this.installStartLock || this.installing || this.installResult)
			return false;

		// 前置检查：后端可达性（如果还没 yes，先同步探活一次并在失败时 toast，不静默）
		if (this.backendReachable !== "yes") {
			const ok = await this.checkBackendConnectivity(true);
			if (!ok) {
				this.installError =
					this.backendLastError || "后端服务器未连接，无法开始安装";
				this.showToast("error", this.installError);
				return false;
			}
		}

		// 管理员配置/站点表单再校验一次（避免用户绕过按钮 gate）
		if (!this.validateSiteAdmin()) {
			this.showToast("error", "请先完善站点信息和管理员账户");
			return false;
		}

		this.installStartLock = true;
		try {
			this.installing = true;
			this.installProgress = 0;
			this.installError = null;
			this.installSteps = [
				{ name: "初始化数据库", status: "active" },
				{ name: "写入配置", status: "idle" },
				{ name: "创建管理员账户", status: "idle" },
				{ name: "生成示例内容", status: "idle" },
				{ name: "构建索引", status: "idle" },
				{ name: "完成安装", status: "idle" },
			];

			const sid = this.uuidv4();
			const payload = this.buildPayload(sid);

			const API_BASE: string =
				typeof (import.meta as any).env?.ROSETTA_API_BASE === "string" &&
				(import.meta as any).env.ROSETTA_API_BASE.trim().length > 0
					? (import.meta as any).env.ROSETTA_API_BASE.trim().replace(/\/$/, "")
					: "/api";

			// === 顺序：先连接 SSE（订阅 sid），再发 POST 触发后端安装
			// 避免先 POST 后 SSE：当 POST 执行很快，进度事件就已经被广播，但 SSE 还没连上就收不到了
			const streamUrl = `${API_BASE}/oobe/install/stream?sid=${encodeURIComponent(sid)}`;
			let es: EventSource | null = null;
			let esClosed = false;
			const closeEs = () => {
				if (!esClosed && es) {
					esClosed = true;
					try {
						es.close();
					} catch {
						/* ignore */
					}
				}
			};
			let sseErrored: string | null = null;
			let finalizeCalled = false;

			const tryFinalize = (data: any) => {
				if (finalizeCalled) return;
				finalizeCalled = true;
				this.finalizeInstall(data);
			};

			let sseConnected = false;
			let sseConnectFailTimer: any = null;

			try {
				es = new EventSource(streamUrl, { withCredentials: false });
				es.addEventListener("connected", () => {
					sseConnected = true;
					if (sseConnectFailTimer) {
						clearTimeout(sseConnectFailTimer);
						sseConnectFailTimer = null;
					}
				});
				es.addEventListener("progress", (ev: any) => {
					try {
						const d = JSON.parse(ev.data || "{}");
						this.updateInstallProgress(d);
					} catch {
						/* ignore */
					}
				});
				es.addEventListener("done", (ev: any) => {
					try {
						const d = ev?.data ? JSON.parse(ev.data) : null;
						tryFinalize(d);
					} catch {
						tryFinalize(null);
					} finally {
						closeEs();
					}
				});
				es.addEventListener("error", (ev: any) => {
					closeEs();
					if (this.installResult) return;
					// SSE 错误先暂存，由下方的 /install POST 失败再决定是否提示（有时候 POST 会成功）
					let msg: string | null = null;
					try {
						if (ev?.data) {
							const d = JSON.parse(ev.data);
							msg = d?.error || d?.message || null;
						}
					} catch {
						/* ignore */
					}
					sseErrored = msg || "安装进度流连接中断";
				});
				// 原生 onerror（无事件 data 时兜底）
				es.onerror = () => {
					if (this.installResult || sseErrored) return;
					sseErrored = "SSE 进度通道连接失败（安装请求仍会继续尝试）";
				};
				// 防 SSE 长时间连不上：若 12s 内一直没 connected 事件，取消等 SSE，直接走 POST
				sseConnectFailTimer = setTimeout(() => {
					if (!sseConnected && !this.installResult) {
						sseErrored = "安装进度通道连接超时，正在使用简化模式安装…";
						try {
							es?.close();
						} catch {
							/* ignore */
						}
					}
				}, 12000);
			} catch (e: any) {
				// EventSource 构造本身就抛错（极少数浏览器/环境）
				sseErrored = e?.message || "不支持安装进度流（EventSource）";
			}

			// 发安装请求
			let installResp: any = null;
			let installErr: string | null = null;
			try {
				installResp = await apiPost<any>("/oobe/install", payload, {
					_timeout: 5 * 60 * 1000,
				});
			} catch (e: any) {
				installErr = e?.message || "安装请求失败";
			}

			if (sseConnectFailTimer) {
				clearTimeout(sseConnectFailTimer);
				sseConnectFailTimer = null;
			}

			// === 结果判定：
			// 1) SSE 已经 done -> 已 finalize
			// 2) 否则看 POST 的结果
			if (!finalizeCalled && installResp) {
				const payloadData = installResp?.data ?? installResp;
				// 后端 CombinedInstallResponse 里 success=true 且带 site_name/admin_username 之类
				const success =
					payloadData?.success === true ||
					payloadData?.installed === true ||
					payloadData?.site_name ||
					payloadData?.frontend_url;
				if (success) {
					tryFinalize(payloadData);
				} else {
					installErr = payloadData?.message || payloadData?.error || "安装失败";
				}
			}

			// === 失败/错误处理：对用户可见，不静默
			if (!this.installResult) {
				const finalErr = installErr
					? sseErrored
						? `${installErr}（${sseErrored}）`
						: installErr
					: sseErrored;
				if (finalErr) {
					this.installError = finalErr;
					this.showToast("error", finalErr);
					// 把当前 active 的步骤标记成 error 状态，让用户知道卡在哪
					this.installSteps = this.installSteps.map((s) =>
						s.status === "active" ? { ...s, status: "error" as StepStatus } : s,
					);
				}
				// 30s 兜底模拟：后端如果完全不响应，也不要永远让用户在 loading
				if (!this.installResult) {
					const fallback = this.simulateFallbackInstall();
					if (fallback) tryFinalize(null);
				}
			}

			closeEs();
			this.installing = false;
			return !!this.installResult;
		} catch (e: any) {
			const msg = e?.message || "安装过程出现未知错误";
			this.installError = msg;
			this.showToast("error", msg);
			this.installing = false;
			return false;
		} finally {
			this.installStartLock = false;
		}
	}

	private buildPayload(sid: string) {
		const f: Record<string, boolean> = {};
		for (const k of Object.keys(OOBE_FEATURE_DEFAULTS))
			f[k] = !!this.draft.features?.[k];
		return {
			sid,
			database_type:
				this.draft.database?.dbType === "postgres" ? "postgresql" : "sqlite",
			db_host: this.draft.database?.dbHost ?? "",
			db_port: this.draft.database?.dbPort ?? 5432,
			db_name: this.draft.database?.dbName ?? "rosetta",
			db_user: this.draft.database?.dbUser ?? "",
			db_password: this.draft.database?.dbPassword ?? "",
			redis_enabled: !!this.draft.database?.redisEnable,
			redis_host: this.draft.database?.redisHost ?? "localhost",
			redis_port: this.draft.database?.redisPort ?? 6379,
			redis_password: this.draft.database?.redisPassword ?? "",
			site_name: this.draft.site?.siteName ?? "Rosetta",
			site_url: this.draft.site?.siteUrl ?? "/",
			site_description: this.draft.site?.siteDescription ?? "",
			site_keywords: this.draft.site?.siteKeywords ?? "",
			site_author: this.draft.site?.siteAuthor ?? "Admin",
			site_email: this.draft.site?.siteEmail ?? "",
			admin_username: this.draft.admin?.adminUsername ?? "",
			admin_email: this.draft.admin?.adminEmail ?? "",
			admin_nickname: this.draft.admin?.adminNickname ?? "",
			admin_password: this.draft.admin?.adminPassword ?? "",
			// 管理员扩展资料（与后端 CombinedInstallRequest 对应）
			admin_bio: "Full-Stack Development",
			admin_qq: "952223950",
			admin_github: "Choyeon",
			admin_website: "https://rosetta.choyeon.cc",
			admin_avatar_source: "auto",
			...f,
		};
	}

	private updateInstallProgress(d: any) {
		if (typeof d?.step === "number") {
			const idx = Math.max(
				0,
				Math.min(this.installSteps.length - 1, d.step - 1),
			);
			this.installSteps = this.installSteps.map((s, i) => {
				if (i < idx) return { ...s, status: "done" as StepStatus };
				if (i === idx) return { ...s, status: "active" as StepStatus };
				return s;
			});
		}
		if (typeof d?.progress === "number") {
			this.installProgress = Math.max(0, Math.min(100, d.progress));
		} else {
			const doneCount = this.installSteps.filter(
				(s) => s.status === "done",
			).length;
			this.installProgress = Math.round(
				(doneCount / this.installSteps.length) * 100,
			);
		}
	}

	private finalizeInstall(d: any) {
		if (this.installResult) return;
		this.installSteps = this.installSteps.map((s) => ({
			...s,
			status: "done" as StepStatus,
		}));
		this.installProgress = 100;
		this.installing = false;
		const siteName = d?.site_name || this.draft.site?.siteName || "Rosetta";
		const adminUser =
			d?.admin_username || this.draft.admin?.adminUsername || "admin";
		const siteUrl =
			d?.frontend_url || d?.site_url || this.draft.site?.siteUrl || "/";
		const adminUrl = d?.admin_url || "/admin/";
		this.installResult = {
			siteName,
			adminUsername: adminUser,
			frontendUrl: siteUrl,
			adminUrl,
		};
		try {
			localStorage.removeItem(DRAFT_KEY);
		} catch {
			/* ignore */
		}
		this.showToast("success", "安装完成！");
	}

	private simulateFallbackInstall(): boolean {
		if (this.installing || this.installResult) return false;
		let i = 0;
		const timer = setInterval(() => {
			if (i >= this.installSteps.length) {
				clearInterval(timer);
				this.finalizeInstall(null);
				return;
			}
			this.installSteps = this.installSteps.map((s, idx) => {
				if (idx < i) return { ...s, status: "done" as StepStatus };
				if (idx === i) return { ...s, status: "active" as StepStatus };
				return s;
			});
			this.installProgress = Math.round(
				((i + 1) / this.installSteps.length) * 100,
			);
			i++;
		}, 700);
		return true;
	}

	// ===== Theme & Lang =====
	private resolveInitialTheme(): ThemeMode {
		try {
			const saved = localStorage.getItem(THEME_STORAGE_KEY);
			if (saved === "light" || saved === "dark") return saved;
			if (saved === "system") {
				const resolved =
					typeof window !== "undefined" &&
					window.matchMedia &&
					window.matchMedia("(prefers-color-scheme: dark)").matches
						? "dark"
						: "light";
				try {
					localStorage.setItem(THEME_STORAGE_KEY, resolved);
				} catch {
					/* ignore */
				}
				return resolved;
			}
		} catch {
			/* ignore */
		}
		if (typeof window !== "undefined" && window.matchMedia) {
			return window.matchMedia("(prefers-color-scheme: dark)").matches
				? "dark"
				: "light";
		}
		return "light";
	}

	applyClass(show: "light" | "dark") {
		this.currentTheme = show;
		const root = document.documentElement;
		if (show === "dark") root.classList.add("dark");
		else root.classList.remove("dark");
	}

	private readHue(): number {
		try {
			const saved = localStorage.getItem(HUE_STORAGE_KEY);
			const n = saved ? Number.parseInt(saved, 10) : Number.NaN;
			if (Number.isFinite(n)) return n;
		} catch {
			/* ignore */
		}
		try {
			const carrier = document.getElementById("config-carrier");
			const raw = carrier?.dataset.hue;
			const n = raw ? Number.parseInt(raw, 10) : Number.NaN;
			if (Number.isFinite(n)) return n;
		} catch {
			/* ignore */
		}
		return DEFAULT_HUE;
	}

	private applyHue(hue: number) {
		document.documentElement.style.setProperty("--hue", String(hue));
	}

	switchTheme(e?: MouseEvent) {
		const target = this.themeMode === "light" ? "dark" : "light";
		this.themeMode = target;
		try {
			localStorage.setItem(THEME_STORAGE_KEY, target);
		} catch {
			/* ignore */
		}
		const targetDark = target === "dark";
		const x = e?.clientX ?? window.innerWidth / 2;
		const y = e?.clientY ?? window.innerHeight / 2;
		void playThemeReveal(x, y, targetDark, () =>
			this.applyClass(targetDark ? "dark" : "light"),
		);
		if (typeof window !== "undefined") {
			window.dispatchEvent(
				new CustomEvent("theme-change", { detail: { mode: target } }),
			);
		}
	}

	modeTitle(m: ThemeMode): string {
		if (m === "light") return "当前：亮色 · 点击切换到暗色";
		return "当前：暗色 · 点击切换到亮色";
	}

	private resolveInitialLang(): string {
		try {
			const saved = localStorage.getItem(LANG_STORAGE_KEY);
			if (saved && OOBE_LANGS.some((L) => L.code === saved)) return saved;
		} catch {
			/* ignore */
		}
		return "zh_CN";
	}

	applyLang(code: string, reload = true) {
		this.currentLang = code;
		try {
			localStorage.setItem(LANG_STORAGE_KEY, code);
		} catch {
			/* ignore */
		}
		this.langPanelOpen = false;
		if (reload) location.reload();
	}

	closeLangPanelOnOutside(e: MouseEvent) {
		const t = e.target as HTMLElement | null;
		if (!t) return;
		const langWrap = t.closest?.("[data-oobe-lang-wrap]");
		if (!langWrap) this.langPanelOpen = false;
	}

	currentLangShort(): string {
		const item = OOBE_LANGS.find((L) => L.code === this.currentLang);
		return item ? item.short : "简中";
	}

	// ===== Quick Install (一键 OOBE) =====
	/**
	 * 一键 OOBE：跳过分步向导，直接使用 draft 中预填的配置启动安装。
	 * 会先探活后端、校验必填项，然后跳转到完成步骤并执行安装。
	 */
	async quickInstall(): Promise<boolean> {
		if (this.installStartLock || this.installing || this.installResult) return false;

		const reachable = await this.checkBackendConnectivity(true);
		if (!reachable) {
			this.showToast("error", this.backendLastError || "无法连接后端服务器");
			return false;
		}
		if (!this.validateSiteAdmin()) {
			this.showToast("error", "管理员信息不完整，请检查用户名/邮箱/密码");
			return false;
		}
		// 跳到第 6 步（完成），然后启动安装
		this.animDir = "next";
		this.stepVisible = false;
		this.saveDraft();
		await new Promise((r) => setTimeout(r, 220));
		this.currentStep = 6;
		this.stepVisible = true;
		return this.startInstall();
	}

	// ===== Init =====
	initOobe() {
		this.applyHue(this.readHue());
		const initial = this.resolveInitialTheme();
		this.themeMode = initial;
		this.applyClass(initial);
		this.currentLang = this.resolveInitialLang();
		document.addEventListener("click", this.closeLangPanelOnOutside.bind(this));
		this.loadDraft();
	}
}

// ===== Singleton export =====
export const oobe = new OobeWizardState();
