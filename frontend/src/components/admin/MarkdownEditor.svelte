<svelte:window on:beforeunload={handleBeforeUnload} />

<script lang="ts">
import { createEventDispatcher, onDestroy, onMount } from "svelte";
import { client } from "../../api/client";

export let value = "";
export let postId: string | number | null = null;
export let language = "zh";
export let disabled = false;

type PostStatus = "draft" | "published" | "scheduled";
type EncryptionData = { salt?: string; verifier?: string; algorithm?: string };
type FnOnValueChange = (val: string) => void;
type FnOnEncryptionChange = (enabled: boolean, data: EncryptionData) => void;
type FnOnScheduledChange = (iso: string, enable: boolean) => void;
type FnOnStatusChange = (s: PostStatus) => void;

export let encryptionEnabled = false;
export let encryptionData: EncryptionData = {};
export let scheduledAt = "";
export let status: PostStatus = "draft";

export let onValueChange: FnOnValueChange | undefined;
export let onEncryptionChange: FnOnEncryptionChange | undefined;
export let onScheduledChange: FnOnScheduledChange | undefined;
export let onStatusChange: FnOnStatusChange | undefined;

type EditorDispatchMap = {
	valueChange: { value: string };
	encryptionChange: { enabled: boolean; data: EncryptionData };
	scheduledChange: { iso: string; enable: boolean };
	statusChange: PostStatus;
	ready: undefined;
};
const dispatch = createEventDispatcher<EditorDispatchMap>();

const DRAFT_KEY_BASE = "rosetta_editor_draft_";

type VditorMode = "ir" | "sd" | "wysiwyg";
let editorMode: VditorMode = "ir";
let vditor: any = null;
let vditorContainer: HTMLDivElement | null = null;
let unsaved = false;
let externalUpdateLock = false;
let setValueTimer: number | null = null;

export function getMarkdown(): string {
	// 安全读取 Vditor 编辑器当前 Markdown 内容。
	// 修复：Vditor 在初始化未完成、after 回调未执行、或组件销毁中时，
	// 其内部 editor.currentMode / currentEditor 等字段可能为 undefined，
	// 直接调用 vditor.getValue() 会抛
	//   "Cannot read properties of undefined (reading 'currentMode')"
	// 这里用 nullish 链 + try/catch 保证稳定。
	try {
		if (vditor && typeof vditor.getValue === "function") {
			const v = vditor.getValue();
			return typeof v === "string" ? v : (value ?? "");
		}
	} catch (e: any) {
		// 未 ready 时忽略（Svelte $: reactive 会在 next tick 再次触发）
		if (
			!e ||
			!(
				String(e?.message).includes("currentMode") ||
				String(e?.name).includes("TypeError")
			)
		) {
			console.warn("[editor] getValue failed:", e);
		}
	}
	return value ?? "";
}

function safeSetValue(newVal: string) {
	try {
		if (vditor && typeof vditor.setValue === "function") {
			vditor.setValue(newVal ?? "");
		}
	} catch (e) {
		console.warn("[editor] setValue failed:", e);
	}
}

/**
 * 事件驱动：把当前 Markdown 内容派发给父组件（Svelte event + DOM CustomEvent 双路）。
 * 这样 PostEditorForm 不需要 window.setInterval 轮询每 700ms 读 props。
 * externalUpdateLock=true 时跳过：避免 safeSetValue/restoreDraft 的外部写入反向触发导致死循环。
 */
function _emitValueChange(override?: string) {
	if (externalUpdateLock) return;
	const v: string = typeof override === "string" ? override : getMarkdown();
	if (typeof v !== "string") return;
	value = v;
	// 1) Svelte 组件级事件（on:valueChange={...}）
	try {
		dispatch("valueChange", { value: v });
	} catch {
		/* ignore */
	}
	// 2) 函数式 prop（兼容旧模式 onValueChange={(v) => ...}）
	try {
		onValueChange?.(v);
	} catch {
		/* ignore */
	}
	// 3) DOM 冒泡 CustomEvent（便于非 Svelte 宿主）
	if (typeof window !== "undefined" && vditorContainer?.ownerDocument) {
		try {
			const host = vditorContainer.closest(
				"[data-md-editor-host], #md-editor-form-host, #md-editor, .pef-md-editor, .antd-md-editor",
			) as Element | null;
			const target = host ?? vditorContainer;
			target?.dispatchEvent(
				new CustomEvent("rosetta:md-change", {
					bubbles: true,
					cancelable: false,
					composed: true,
					detail: { value: v },
				}),
			);
		} catch {
			/* ignore */
		}
	}
}

function customPrompt(msg: string, defaultValue = ""): string | null {
	// 修复："prompt() is not supported" — 某些沙箱浏览器、WebView、扩展脚本
	// 环境中禁用了原生 prompt/confirm/alert；优先用原生，失败时降级为简单输入。
	try {
		const r = (globalThis as any).prompt?.(msg, defaultValue);
		if (typeof r === "string") return r;
		if (r === null) return null;
	} catch (_) {
		/* 禁用时回退 */
	}
	const r2 = (globalThis as any).window?.prompt?.(msg, defaultValue);
	if (typeof r2 === "string") return r2;
	if (r2 === null) return null;
	// 最后的保底：提示用户用 console 输入（返回 null 表示取消）
	alert?.(
		"当前浏览器不支持 prompt 弹窗，请先手动打开开发者工具（F12）输入：\n" +
			`  __encPwd1 = prompt('${msg.replace(/'/g, "\\'")}', '${defaultValue.replace(/'/g, "\\'")}')\n` +
			"再重新点击复选框。",
	);
	return null;
}

async function deriveKeys(pwd: string) {
	const r = await client.post("/api/post_crypto/derive_keys", {
		password: pwd,
	});
	return r.data as { salt: string; verifier: string; algorithm: string };
}

function doDisableEncrypt() {
	encryptionEnabled = false;
	encryptionData = {};
	onEncryptionChange?.(false, {});
}

function handleEncryptionCheckboxChange(e: Event) {
	const checked = (e.target as HTMLInputElement).checked;
	if (checked) {
		const pwd1 = customPrompt("请设置加密密码（至少 6 位）：", "");
		if (!pwd1 || pwd1.length < 6) {
			alert("密码至少 6 位");
			(e.target as HTMLInputElement).checked = false;
			return;
		}
		const pwd2 = customPrompt("请再次输入密码确认：", "");
		if (pwd1 !== pwd2) {
			alert("两次输入的密码不一致");
			(e.target as HTMLInputElement).checked = false;
			return;
		}
		deriveKeys(pwd1)
			.then((keys) => {
				encryptionEnabled = true;
				encryptionData = keys;
				onEncryptionChange?.(true, keys);
			})
			.catch((err) => {
				console.error(err);
				alert("派生密钥失败");
				(e.target as HTMLInputElement).checked = false;
			});
	} else {
		doDisableEncrypt();
	}
}

function handleScheduledAt(v: string) {
	scheduledAt = v;
	const enable = !!v;
	if (enable && status !== "scheduled") {
		status = "scheduled";
		onStatusChange?.("scheduled");
	}
	onScheduledChange?.(v, enable);
}

const autosaveTimer = { current: null as number | null };
function scheduleAutosave() {
	if (typeof window === "undefined") return;
	if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current);
	autosaveTimer.current = window.setTimeout(() => saveDraft(), 3000);
}

function draftKey() {
	const id = postId ?? `new-${language}`;
	return DRAFT_KEY_BASE + id;
}

function saveDraft(silent = false) {
	if (typeof localStorage === "undefined") return;
	try {
		localStorage.setItem(
			draftKey(),
			JSON.stringify({
				value,
				ts: Date.now(),
				language,
				encryptionEnabled,
				encryptionData,
				scheduledAt,
				status,
			}),
		);
		unsaved = false;
		if (!silent) console.debug("[editor] draft saved");
	} catch (e) {
		console.warn("[editor] save draft failed", e);
	}
}

function restoreDraft() {
	try {
		const raw = localStorage.getItem(draftKey());
		if (!raw) return;
		const d = JSON.parse(raw);
		if (d.value) {
			const ok = confirm("恢复上次未保存的草稿？");
			if (!ok) return;
			value = d.value;
			encryptionEnabled = !!d.encryptionEnabled;
			encryptionData = d.encryptionData || {};
			scheduledAt = d.scheduledAt || "";
			status = d.status || "draft";
			unsaved = true;
			onEncryptionChange?.(encryptionEnabled, encryptionData);
			onStatusChange?.(status);
			onScheduledChange?.(scheduledAt, !!scheduledAt);
			if (vditor) {
				externalUpdateLock = true;
				vditor.setValue(value);
				setTimeout(() => (externalUpdateLock = false), 50);
			}
		}
	} catch (e) {
		console.warn("[editor] restore draft failed", e);
	}
}

function handleBeforeUnload(e: BeforeUnloadEvent) {
	if (unsaved) {
		saveDraft();
		e.preventDefault();
		e.returnValue = "";
		return "";
	}
}

async function customUploadRequest(
	editor: any,
	files: File[] | null,
): Promise<void> {
	if (!files?.length) return;
	for (const f of files) {
		try {
			const formData = new FormData();
			formData.append("file", f);
			const r = await client.post("/api/media/upload", formData, {
				headers: { "Content-Type": "multipart/form-data" },
			});
			const url = (r.data as any)?.url || (r.data as any)?.data?.url;
			if (url) {
				editor.insertValue(`![${f.name}](${url})`);
			} else {
				alert("上传成功但未获取到图片 URL");
			}
		} catch (e) {
			console.error("upload image failed", e);
			alert(`上传失败：${(e as any).message}`);
		}
	}
}

async function initVditor() {
	if (!vditorContainer) return;
	const VditorMod = await import("vditor");
	await import("vditor/dist/index.css");
	const Vditor = VditorMod.default;

	const toolbarItems = [
		"emoji",
		"headings",
		"bold",
		"italic",
		"strike",
		"|",
		"line",
		"quote",
		"list",
		"ordered-list",
		"check",
		"outdent",
		"indent",
		"|",
		"code-theme-select",
		"code",
		"inline-code",
		"insert-before",
		"insert-after",
		"|",
		"link",
		"image",
		"upload-image",
		"table",
		"chart",
		"mermaid",
		"plantuml",
		"math",
		"mindmap",
		"|",
		"split-view",
		"both",
		"preview",
		"outline",
		"|",
		"fullscreen",
		"preview-tools",
		"br",
		"both-preview",
		"file-tools",
		"edit-mode",
		"|",
		"undo",
		"redo",
		"|",
		"export",
		"speech-commit",
		"help",
	];

	vditor = new Vditor(vditorContainer, {
		mode: editorMode,
		height: 720,
		placeholder: "开始写作… 空行输入 / 打开快捷菜单",
		outline: { enable: true, position: "right" },
		typewriterMode: true,
		cache: { enable: false },
		preview: {
			markdown: {
				toc: true,
				mark: true,
				footnotes: true,
				autoSpace: true,
				fixTermTypo: true,
			},
			math: { engine: "KaTeX" as const },
			mermaid: true,
			chart: true,
			plantuml: { openMarker: "@startuml", closeMarker: "@enduml" },
			katexFontPath: "https://unpkg.com/katex@0.16.11/dist/fonts/",
		},
		toolbar: toolbarItems,
		upload: {
			url: "/api/media/upload",
			fileFieldName: "file",
			customRequest: (_xhr: any, files: File[]) => {
				customUploadRequest(vditor, files);
			},
		},
		input: () => {
			if (externalUpdateLock) return;
			// 修复：Vditor 的 input 在某些版本中会在编辑器完全 ready 之前
			// 触发（此时 currentEditor/currentMode 未初始化），用安全的
			// getMarkdown() 包装避免 TypeError。
			const next = getMarkdown();
			if (typeof next === "string") value = next;
			// 事件驱动：把内容变化派发给 PostEditorForm（Svelte event + DOM CustomEvent）
			// 干掉原来 Astro 页面里 setInterval(poll, 700/800ms) 的轮询逻辑
			_emitValueChange(typeof next === "string" ? next : undefined);
			unsaved = true;
			scheduleAutosave();
		},
		after: () => {
			if (value) {
				safeSetValue(value);
			}
		},
	});
}

function switchMode(mode: VditorMode) {
	editorMode = mode;
	// 修复："$.get(...).setMode is not a function" —
	// 不同 Vditor 版本 API 不完全兼容，且在实例未 ready / 已销毁
	// 时 vditor.setMode 可能不是函数。采用链式 try + 双 API 兜底。
	try {
		if (!vditor) return;
		if (typeof vditor.setMode === "function") {
			vditor.setMode(mode);
		} else if (typeof (vditor as any).editor?.setMode === "function") {
			(vditor as any).editor.setMode(mode);
		} else if (typeof (vditor as any).switchMode === "function") {
			(vditor as any).switchMode(mode);
		}
	} catch (e) {
		console.warn("[editor] switchMode failed:", mode, e);
	}
}

$: if (typeof window !== "undefined" && vditor && !externalUpdateLock) {
	if (setValueTimer) window.clearTimeout(setValueTimer);
	setValueTimer = window.setTimeout(() => {
		const cur = getMarkdown();
		if (cur !== value) {
			externalUpdateLock = true;
			safeSetValue(value);
			setTimeout(() => (externalUpdateLock = false), 50);
		}
	}, 80);
}

onMount(() => {
	initVditor().then(() => {
		restoreDraft();
	});
});

onDestroy(() => {
	saveDraft();
	if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current);
	if (setValueTimer) window.clearTimeout(setValueTimer);
	if (vditor) {
		try {
			vditor.destroy();
		} catch {
			/* ignore */
		}
	}
});
</script>

<div class="milkdown-editor">
	<div class="me-toolbar">
		<label class="me-field">
			<input
				type="checkbox"
				checked={encryptionEnabled}
				disabled={disabled}
				on:change={handleEncryptionCheckboxChange} />
			<span>启用加密</span>
		</label>

		<label class="me-field">
			<input
				type="datetime-local"
				value={scheduledAt}
				disabled={disabled}
				on:input={(e) => handleScheduledAt((e.target as HTMLInputElement).value)} />
			<span>定时发布</span>
		</label>

		<select
			class="me-select"
			value={status}
			disabled={disabled}
			on:change={(e) => onStatusChange?.((e.target as HTMLSelectElement).value as PostStatus)}>
			<option value="draft">草稿</option>
			<option value="published">已发布</option>
			<option value="scheduled">定时</option>
		</select>

		<span class="me-divider" />

		<div class="me-mode-group" role="group" aria-label="编辑器模式">
			<button
				type="button"
				class:me-active={editorMode === "ir"}
				class="me-mode-btn"
				disabled={disabled}
				on:click={() => switchMode("ir")}>
				即时渲染
			</button>
			<button
				type="button"
				class:me-active={editorMode === "sd"}
				class="me-mode-btn"
				disabled={disabled}
				on:click={() => switchMode("sd")}>
				分栏
			</button>
			<button
				type="button"
				class:me-active={editorMode === "wysiwyg"}
				class="me-mode-btn"
				disabled={disabled}
				on:click={() => switchMode("wysiwyg")}>
				所见即所得
			</button>
		</div>
	</div>

	<div bind:this={vditorContainer} class="me-vditor-host" />
</div>

<style>
	.milkdown-editor {
		display: flex;
		flex-direction: column;
		border: 1px solid hsl(var(--b3));
		border-radius: 12px;
		overflow: hidden;
		background: hsl(var(--b1));
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04), 0 6px 18px rgba(0, 0, 0, 0.05);
	}

	.me-toolbar {
		padding: 0.55rem 0.85rem;
		border-bottom: 1px solid hsl(var(--b3));
		background: color-mix(in srgb, var(--paper-200, hsl(40, 50%, 96%)) 70%, transparent);
		display: flex;
		align-items: center;
		gap: 0.6rem;
		flex-wrap: wrap;
		border-top-left-radius: 10px;
		border-top-right-radius: 10px;
	}

	.me-divider {
		width: 1px;
		background: hsl(var(--b3));
		align-self: stretch;
		margin: 0.2rem 0.25rem;
	}

	.me-field {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 12.5px;
		color: hsl(var(--bc) / 0.75);
	}

	.me-field input[type="checkbox"] {
		width: 1rem;
		height: 1rem;
		accent-color: var(--ochre-400, hsl(35, 85%, 50%));
		cursor: pointer;
	}

	.me-field input[type="datetime-local"] {
		padding: 0.3rem 0.5rem;
		border-radius: 8px;
		border: 1px solid hsl(var(--b3));
		background: hsl(var(--b1));
		color: hsl(var(--bc));
		font-size: 12.5px;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}

	.me-field input[type="datetime-local"]:focus {
		outline: none;
		border-color: var(--ochre-400, hsl(35, 85%, 50%));
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--ochre-400, hsl(35, 85%, 50%)) 25%, transparent);
	}

	.me-select {
		padding: 0.3rem 0.6rem;
		border-radius: 8px;
		border: 1px solid hsl(var(--b3));
		background: hsl(var(--b1));
		color: hsl(var(--bc));
		font-size: 12.5px;
		cursor: pointer;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}

	.me-select:focus {
		outline: none;
		border-color: var(--ochre-400, hsl(35, 85%, 50%));
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--ochre-400, hsl(35, 85%, 50%)) 25%, transparent);
	}

	.me-mode-group {
		margin-left: auto;
		display: inline-flex;
		align-items: center;
		border: 1px solid hsl(var(--b3));
		border-radius: 8px;
		overflow: hidden;
		background: hsl(var(--b1));
	}

	.me-mode-btn {
		all: unset;
		padding: 0.3rem 0.65rem;
		font-size: 12.5px;
		color: hsl(var(--bc) / 0.75);
		cursor: pointer;
		transition: background 0.15s ease, color 0.15s ease;
		border-right: 1px solid hsl(var(--b3));
	}

	.me-mode-btn:last-child {
		border-right: none;
	}

	.me-mode-btn:hover:not([disabled]) {
		background: color-mix(in srgb, var(--ochre-400, hsl(35, 85%, 50%)) 10%, transparent);
		color: hsl(var(--bc));
	}

	.me-mode-btn[disabled] {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.me-mode-btn.me-active {
		background: color-mix(in srgb, var(--ochre-400, hsl(35, 85%, 50%)) 22%, transparent);
		color: hsl(30, 90%, 30%);
		font-weight: 600;
	}

	.me-vditor-host {
		width: 100%;
	}

	.me-vditor-host :global(.vditor) {
		border: none;
		border-radius: 0;
	}

	.me-vditor-host :global(.vditor-toolbar) {
		border-top: none;
		border-left: none;
		border-right: none;
	}

	.me-vditor-host :global(.vditor-reset) {
		background: hsl(var(--b1));
		color: hsl(var(--bc));
	}
</style>
