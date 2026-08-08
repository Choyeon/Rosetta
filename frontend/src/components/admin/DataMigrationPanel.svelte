<script lang="ts">
	import { onMount } from "svelte";
	import Icon from "@components/common/Icon.svelte";
	import { adminApi } from "@api/client";

	// ---------- Types ----------
	interface Presets {
		sqlite_default: string;
		current_database: string;
		current_redis?: string;
	}
	interface MigrationJob {
		job_id: string;
		source: string;
		target: string;
		dry_run: boolean;
		skip_schema: boolean;
		status: "pending" | "running" | "done" | "error" | "cancelled";
		created_at: number;
		started_at?: number;
		finished_at?: number;
		latest_progress?: Record<string, any> | null;
		events_count: number;
		events_tail: Record<string, any>[];
		errors: string[];
		warnings: string[];
	}

	// ---------- State ----------
	let presets: Presets | null = null;
	let loadingPresets = false;
	let sourceUrl = "";
	let targetUrl = "";
	let dryRun = false;
	let skipSchema = false;
	let submitting = false;
	let cancelling = false;
	let pollingTimer: number | null = null;
	let job: MigrationJob | null = null;
	let autoScroll = true;
	let eventsEl: HTMLDivElement | undefined;

	// ---------- IO ----------
	async function loadPresets() {
		loadingPresets = true;
		try {
			const res = await adminApi.get<any>("/admin/migration/presets");
			if (res?.success && res?.presets) {
				presets = res.presets as Presets;
				if (!sourceUrl) sourceUrl = presets.current_database || presets.sqlite_default;
				if (!targetUrl) targetUrl = presets.current_database;
			}
		} catch (e) {
			console.warn("[migration] presets load failed", e);
		} finally {
			loadingPresets = false;
		}
	}

	async function refreshStatus() {
		try {
			const res = await adminApi.get<any>("/admin/migration/status");
			if (res?.success) job = res.job || null;
		} catch (e) {
			console.warn("[migration] status fetch failed", e);
		}
	}

	async function start() {
		if (!sourceUrl.trim() || !targetUrl.trim()) return;
		submitting = true;
		try {
			const res = await adminApi.post<any>("/admin/migration/start", {
				source: sourceUrl.trim(),
				target: targetUrl.trim(),
				dry_run: dryRun,
				skip_schema: skipSchema,
			});
			if (res?.success) {
				job = res.job as MigrationJob;
				startPolling();
			}
		} catch (e: any) {
			alert("启动迁移失败：" + (e?.message || e));
		} finally {
			submitting = false;
		}
	}

	async function cancel() {
		if (!job) return;
		cancelling = true;
		try {
			const res = await adminApi.post<any>("/admin/migration/cancel", {});
			if (res?.success) {
				job = res.job as MigrationJob;
				stopPolling();
			}
		} catch (e) {
			alert("取消失败：" + (e as any)?.message);
		} finally {
			cancelling = false;
		}
	}

	function startPolling() {
		stopPolling();
		pollingTimer = window.setInterval(async () => {
			await refreshStatus();
			if (job && job.status !== "running" && job.status !== "pending") {
				stopPolling();
			}
			// auto scroll
			if (autoScroll && eventsEl) {
				eventsEl.scrollTop = eventsEl.scrollHeight;
			}
		}, 1500);
	}

	function stopPolling() {
		if (pollingTimer) {
			clearInterval(pollingTimer);
			pollingTimer = null;
		}
	}

	function applyPreset(kind: "sqlite_default" | "current_database" | "current_redis", where: "src" | "dst") {
		if (!presets) return;
		const v = (presets as any)[kind] as string | undefined;
		if (!v) return;
		if (where === "src") sourceUrl = v;
		else targetUrl = v;
	}

	$: elapsed = (job?.started_at && job?.finished_at)
		? (job.finished_at - job.started_at) / 1000
		: job?.started_at
			? (Date.now() - job.started_at) / 1000
			: 0;
	// Tick for live elapsed timer
	let t = 0;
	setInterval(() => { t++; $elapsed = t; }, 1000);
	// NOTE: use reactive statement trick below
</script>

<div class="antd-migration-card">
	<div class="card-head">
		<div class="title">
			<Icon icon="material-symbols:database-move-outline-sharp" w={22} h={22} style="color:#1677ff" />
			<h2>数据一键迁移</h2>
		</div>
		<p class="desc">
			支持 SQLite ↔ PostgreSQL 之间的跨库数据迁移，将自动完成 <b>建表 schema</b>（Alembic）、<b>外键暂停</b>、<b>批量插入</b>、<b>序列重置</b>与<b>行数校验</b>。
			单实例全局同时只运行一个任务，运行中可轮询 <b>/api/admin/migration/status</b> 查看进度。
		</p>
	</div>

	<!-- Presets -->
	<div class="presets">
		<button type="button" class="antd-btn antd-btn-default" disabled={loadingPresets || !presets}
			on:click={() => applyPreset("sqlite_default", "src")}>源: 用 SQLite 默认</button>
		<button type="button" class="antd-btn antd-btn-default" disabled={loadingPresets || !presets}
			on:click={() => applyPreset("current_database", "src")}>源: 当前实例 DB</button>
		<button type="button" class="antd-btn antd-btn-default" disabled={loadingPresets || !presets}
			on:click={() => applyPreset("current_database", "dst")}>目标: 当前实例 DB</button>
		<button type="button" class="antd-btn antd-btn-ghost" on:click={loadPresets}>
			{loadingPresets ? "加载中..." : "刷新预设"}
		</button>
	</div>

	<!-- Form -->
	<div class="form-grid">
		<div class="form-item">
			<label>源库 URL（SQLAlchemy）</label>
			<input class="antd-input" bind:value={sourceUrl}
				placeholder="sqlite+aiosqlite:///./rosetta.db" />
			<span class="hint">示例：sqlite+aiosqlite:///./rosetta.db &nbsp; 或 &nbsp; postgresql+asyncpg://user:pass@host:5432/db</span>
		</div>
		<div class="form-item">
			<label>目标库 URL（SQLAlchemy）</label>
			<input class="antd-input" bind:value={targetUrl}
				placeholder="postgresql+asyncpg://rosetta:secret@localhost:5432/rosetta" />
			<span class="hint">PG 目标库如果不存在，将自动通过维护库 <b>postgres</b> CREATE DATABASE（需连接账号有超级用户或 CREATEDB 权限）。</span>
		</div>
		<div class="form-item checkboxes">
			<label class="chk"><input type="checkbox" bind:checked={dryRun} /> 仅 Dry-run（不写目标，只列计数）</label>
			<label class="chk"><input type="checkbox" bind:checked={skipSchema} /> 跳过 Alembic schema 升级（目标已确保 schema 最新时选）</label>
		</div>
	</div>

	<!-- Actions -->
	<div class="actions">
		<button class="antd-btn antd-btn-primary"
			disabled={submitting || !sourceUrl || !targetUrl || (job?.status === "running")}
			on:click={start}>
			{submitting ? "提交中..." : job?.status === "running" ? "迁移中..." : "🚀 开始迁移"}
		</button>
		<button class="antd-btn antd-btn-danger"
			disabled={cancelling || job?.status !== "running"}
			on:click={cancel}>
			{cancelling ? "取消中..." : "强制停止"}
		</button>
		<button class="antd-btn antd-btn-default" on:click={refreshStatus}>拉取最新状态</button>
	</div>

	<!-- Job status -->
	{#if job}
		<div class="status-card">
			<div class="status-grid">
				<div><b>任务ID</b> <code>{job.job_id.slice(0, 12)}…</code></div>
				<div><b>状态</b>
					<span class="badge badge-{job.status}">{job.status.toUpperCase()}</span>
				</div>
				<div><b>源</b> <code>{job.source}</code></div>
				<div><b>目标</b> <code>{job.target}</code></div>
				<div><b>Dry-run</b> {String(job.dry_run)}</div>
				<div><b>Skip-schema</b> {String(job.skip_schema)}</div>
				<div><b>进度</b>
					{job.latest_progress?.tables_done ?? 0}/{job.latest_progress?.tables_total ?? 0} 表 ·
					{job.latest_progress?.rows_done ?? 0}/{job.latest_progress?.rows_total ?? 0} 行
				</div>
				<div><b>耗时</b>
					{#if job.started_at}
						{job.finished_at
							? ((job.finished_at - job.started_at) / 1000).toFixed(1) + "s"
							: ((Date.now() - job.started_at) / 1000).toFixed(1) + "s (运行中)"}
					{:else}-{/if}
				</div>
				<div><b>警告</b> <span class="warn">{job.warnings.length}</span></div>
				<div><b>错误</b> <span class="err">{job.errors.length}</span></div>
			</div>

			{#if job.errors.length}
				<div class="list err-list">
					{#each job.errors.slice(-12) as e, i}
						<div class="line err">❌ {e}</div>
					{/each}
				</div>
			{/if}

			<div class="events-head">
				<h3>事件日志（最多显示最后 200 条，共 {job.events_count}）</h3>
				<label class="chk"><input type="checkbox" bind:checked={autoScroll} /> 自动滚到底部</label>
			</div>
			<div class="events" bind:this={eventsEl}>
				{#each job.events_tail as ev}
					<div class="ev ev-{ev.stage}">
						<span class="time">{ev.elapsed}s</span>
						<span class="stage">{ev.stage}</span>
						<span class="tbl">{ev.table ?? ""}</span>
						<span class="msg">{ev.message ?? ""}{(ev.rows_src ?? null) != null ? ` src=${ev.rows_src}` : ""}{(ev.rows_done ?? null) != null ? ` done=${ev.rows_done}` : ""}</span>
					</div>
				{:else}
					<div class="ev-empty">暂无事件，提交任务后开始刷新</div>
				{/each}
			</div>
		</div>
	{/if}

	<div class="notice danger">
		⚠️ <b>注意：</b>请迁移前备份好源库。SQLite → PG 迁移为了最大兼容性默认使用 <code>INSERT OR IGNORE</code>/<code>ON CONFLICT DO NOTHING</code>，不会覆盖目标已有主键。如遇行数不一致警告，多半是目标存在冲突主键，请先清空目标库再迁。
	</div>
</div>

<svelte:window on:unload={() => stopPolling()} />

<style>
	.antd-migration-card {
		background: #fff;
		border: 1px solid var(--antd-border-default, #e5e7eb);
		border-radius: 12px;
		padding: 20px;
		color: var(--antd-text-primary, rgba(0, 0, 0, 0.88));
	}
	.card-head { margin-bottom: 12px; }
	.title { display: flex; align-items: center; gap: 10px; }
	.title h2 { font-size: 18px; margin: 0; }
	.desc { margin: 6px 0 0 32px; color: rgba(0,0,0,.55); font-size: 13px; }

	.presets { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }

	.form-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
		gap: 14px 20px;
		margin: 16px 0;
	}
	.form-item { display: flex; flex-direction: column; gap: 4px; }
	.form-item label { font-weight: 600; font-size: 13px; }
	.form-item input.antd-input { width: 100%; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
	.form-item .hint { color: rgba(0,0,0,.5); font-size: 12px; }
	.form-item.checkboxes { flex-direction: row; gap: 18px; align-items: center; }
	.chk { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; cursor: pointer; }

	.actions { display: flex; gap: 8px; margin: 4px 0 16px; flex-wrap: wrap; }
	.antd-btn {
		display: inline-flex; align-items: center; justify-content: center;
		height: 34px; padding: 0 14px; border-radius: 8px;
		border: 1px solid var(--antd-border-default, #d9d9d9); cursor: pointer; font-size: 13px;
		background: #fff; color: rgba(0,0,0,.85); transition: .15s all;
	}
	.antd-btn:disabled { opacity: .5; cursor: not-allowed; }
	.antd-btn-primary { background: #1677ff; color: #fff; border-color: #1677ff; }
	.antd-btn-primary:hover:not(:disabled) { background: #4096ff; border-color: #4096ff; }
	.antd-btn-danger { background: #fff; color: #ff4d4f; border-color: #ffccc7; }
	.antd-btn-danger:hover:not(:disabled) { background: #fff2f0; border-color: #ff7875; }
	.antd-btn-default:hover:not(:disabled) { color: #4096ff; border-color: #4096ff; }
	.antd-btn-ghost { background: transparent; }

	.status-card {
		margin: 14px 0;
		background: linear-gradient(180deg, #f8faff, #ffffff);
		border: 1px dashed #c7dbff;
		border-radius: 12px; padding: 14px;
	}
	.status-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 6px 18px;
		font-size: 13px;
	}
	.status-grid code {
		background: #eef2ff; padding: 1px 6px; border-radius: 6px; font-size: 12px;
		word-break: break-all;
	}
	.badge {
		display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700;
	}
	.badge-running { background: #e6f4ff; color: #1677ff; }
	.badge-done { background: #f6ffed; color: #389e0d; }
	.badge-error { background: #fff2f0; color: #cf1322; }
	.badge-cancelled { background: #fff7e6; color: #d46b08; }
	.badge-pending { background: #f5f5f5; color: #8c8c8c; }
	.warn { color: #d46b08; font-weight: 600; }
	.err { color: #cf1322; font-weight: 600; }

	.list { margin: 10px 0; padding: 10px 12px; border-radius: 8px; max-height: 180px; overflow: auto; }
	.err-list { background: #fff2f0; color: #cf1322; }
	.line { font-size: 12px; padding: 2px 0; }

	.events-head { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
	.events-head h3 { margin: 0; font-size: 14px; }
	.events {
		margin-top: 6px;
		background: #0b1020; color: #e5e7eb;
		border-radius: 8px; max-height: 280px; overflow: auto;
		padding: 8px 10px; font-size: 12px; font-family: ui-monospace, Menlo, Consolas, monospace;
	}
	.ev { padding: 2px 0; display: flex; gap: 8px; }
	.ev .time { width: 64px; color: #9ca3af; }
	.ev .stage { width: 64px; font-weight: 700; text-transform: uppercase; }
	.ev-init .stage { color: #60a5fa; }
	.ev-schema .stage { color: #a78bfa; }
	.ev-pre_copy, .ev-verify .stage { color: #f59e0b; }
	.ev-copy .stage { color: #34d399; }
	.ev-done .stage { color: #22c55e; font-weight: 800; }
	.ev-error .stage { color: #f87171; }
	.ev .tbl { min-width: 140px; color: #c7d2fe; font-weight: 600; }
	.ev-empty { color: #6b7280; padding: 10px; text-align: center; }

	.notice {
		margin-top: 16px; padding: 10px 12px; border-radius: 8px; font-size: 12.5px;
	}
	.notice.danger { background: #fffbe6; border: 1px solid #ffe58f; color: #613400; }
</style>
