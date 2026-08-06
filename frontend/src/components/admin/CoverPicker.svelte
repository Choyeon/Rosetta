<script lang="ts">
import { createEventDispatcher } from "svelte";

export let coverUrl: string | null = null;
export let disabled = false;
export let uploadEndpoint = "/api/media/upload";

const dispatch = createEventDispatcher<{
	change: string | null;
}>();

let inputVal = coverUrl ?? "";
let isDragging = false;
let isUploading = false;
let fileInput: HTMLInputElement | null = null;
let errorMsg = "";

$: if (coverUrl !== undefined) inputVal = coverUrl ?? "";

function sync(v: string | null) {
	coverUrl = v;
	inputVal = v ?? "";
	dispatch("change", v);
}

function onInput(e: Event) {
	const v = (e.target as HTMLInputElement).value;
	inputVal = v;
	const clean = v.trim();
	sync(clean || null);
	errorMsg = "";
}

function onBlur() {
	const clean = inputVal.trim();
	sync(clean || null);
}

function clearCover(e: Event) {
	e.preventDefault();
	e.stopPropagation();
	if (disabled) return;
	sync(null);
}

function onPickFileClick(e: Event) {
	if (disabled) return;
	e.preventDefault();
	fileInput?.click();
}

async function handleFiles(list: FileList | null | undefined) {
	if (!list || list.length === 0) return;
	const file = list[0];
	if (!file.type.startsWith("image/")) {
		errorMsg = "请选择图片文件（JPG/PNG/WebP 等）";
		return;
	}
	errorMsg = "";
	// First try upload; if endpoint fails, fall back to objectURL locally (unsaved)
	isUploading = true;
	try {
		const fd = new FormData();
		fd.append("file", file);
		const resp = await fetch(uploadEndpoint, {
			method: "POST",
			body: fd,
			credentials: "same-origin",
		});
		if (resp.ok) {
			const data = await resp.json().catch(() => ({}));
			const url: string | undefined =
				data?.url ?? data?.data?.url ?? data?.path;
			if (url) {
				sync(url);
				return;
			}
		}
		throw new Error(`上传失败 ${resp.status}`);
	} catch (e) {
		// upload unavailable: fallback to objectURL preview (NOT persisted)
		const fallback = URL.createObjectURL(file);
		sync(fallback);
		errorMsg = "上传接口不可用，当前仅为本地预览，保存后不会带图";
	} finally {
		isUploading = false;
	}
}

function onDrop(e: DragEvent) {
	if (disabled) return;
	e.preventDefault();
	isDragging = false;
	handleFiles(e.dataTransfer?.files);
}
function onDragOver(e: DragEvent) {
	if (disabled) return;
	e.preventDefault();
	isDragging = true;
}
function onDragLeave(e: DragEvent) {
	if (disabled) return;
	e.preventDefault();
	isDragging = false;
}
</script>

<div class="cv-wrap" class:cv-disabled={disabled}>
  <div
    class="cv-preview"
    class:cv-drag={isDragging}
    role="img"
    aria-label={coverUrl ? "封面预览" : "封面预览占位"}
    on:dragover={onDragOver}
    on:dragleave={onDragLeave}
    on:drop={onDrop}
    on:click={onPickFileClick}
    title={coverUrl ? "点击更换封面 / 拖拽图片到此处" : "点击选择图片 / 拖拽图片到此处"}
  >
    {#if coverUrl}
      <img src={coverUrl} alt="封面" loading="lazy" referrerpolicy="no-referrer" />
      {#if !disabled}
        <button
          type="button"
          class="cv-remove"
          aria-label="移除封面"
          on:mousedown|stopPropagation={clearCover}
          on:touchstart|stopPropagation={clearCover}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      {/if}
    {:else}
      <div class="cv-empty">
        <svg class="cv-empty-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
        <span class="cv-empty-text">{isUploading ? "上传中…" : "拖拽图片到此处，或点击选择"}</span>
      </div>
    {/if}
    {#if isUploading}
      <div class="cv-spinner" aria-hidden="true"></div>
    {/if}
  </div>
  <input
    bind:this={fileInput}
    type="file"
    accept="image/*"
    style="display:none"
    on:change={(e) => handleFiles((e.target as HTMLInputElement).files)}
  />
  <input
    type="text"
    class="cv-url-input"
    bind:value={inputVal}
    placeholder="粘贴封面图片 URL（https://…）"
    {disabled}
    autocomplete="off"
    spellcheck="false"
    on:input={onInput}
    on:blur={onBlur}
  />
  {#if errorMsg}
    <div class="cv-error" role="alert">{errorMsg}</div>
  {/if}
</div>

<style lang="css">
  .cv-wrap {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .cv-wrap.cv-disabled {
    opacity: 0.6;
    pointer-events: none;
  }
  .cv-preview {
    position: relative;
    aspect-ratio: 16 / 9;
    width: 100%;
    border-radius: 8px;
    overflow: hidden;
    background: linear-gradient(180deg, var(--walnut-50, hsl(40 30% 96%)), var(--walnut-100, hsl(40 25% 92%)));
    border: 1px dashed var(--walnut-200, hsl(30 14% 86%));
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: border-color 160ms ease, background-color 160ms ease, transform 100ms ease;
  }
  .cv-preview:hover {
    border-color: var(--ochre-400, hsl(35 85% 50%));
  }
  .cv-preview.cv-drag {
    border-color: var(--sage-500, hsl(170 60% 38%));
    background: color-mix(in srgb, var(--sage-500, hsl(170 60% 38%)) 10%, var(--walnut-50, hsl(40 30% 96%)));
    transform: scale(1.005);
  }
  .cv-preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .cv-remove {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 28px;
    height: 28px;
    border-radius: 9999px;
    background: color-mix(in srgb, #000 48%, transparent);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    cursor: pointer;
    transition: background-color 140ms ease, transform 100ms ease;
    backdrop-filter: blur(4px);
  }
  .cv-remove:hover {
    background: color-mix(in srgb, #000 68%, transparent);
    transform: scale(1.04);
  }
  .cv-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    color: var(--walnut-400, hsl(24 10% 55%));
    text-align: center;
    padding: 16px;
  }
  .cv-empty-icon {
    opacity: 0.8;
  }
  .cv-empty-text {
    font-size: 0.82rem;
    line-height: 1.5;
  }
  .cv-spinner {
    position: absolute;
    inset: 0;
    background: color-mix(in srgb, #fff 55%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cv-spinner::after {
    content: "";
    width: 28px;
    height: 28px;
    border-radius: 9999px;
    border: 3px solid color-mix(in srgb, var(--ochre-500, hsl(35 85% 50%)) 40%, transparent);
    border-top-color: var(--ochre-500, hsl(35 85% 50%));
    animation: cv-spin 0.8s linear infinite;
  }
  @keyframes cv-spin {
    to { transform: rotate(360deg); }
  }
  .cv-url-input {
    width: 100%;
    height: 32px;
    padding: 4px 11px;
    font-size: 14px;
    line-height: 1.5715;
    color: var(--walnut-700, hsl(24 10% 20%));
    background: var(--input-bg, var(--card-bg, #fff));
    border: 1px solid var(--hairline, hsl(30 14% 86%));
    border-radius: 6px;
    transition: border-color 160ms ease, box-shadow 160ms ease;
    outline: none;
    box-sizing: border-box;
    font-family: inherit;
  }
  .cv-url-input:hover {
    border-color: var(--ochre-400, hsl(35 85% 50%));
  }
  .cv-url-input:focus {
    border-color: var(--ochre-500, hsl(35 85% 50%));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--ochre-500, hsl(35 85% 50%)) 25%, transparent);
  }
  .cv-url-input::placeholder {
    color: color-mix(in srgb, var(--walnut-500, hsl(24 10% 45%)) 70%, transparent);
  }
  .cv-error {
    font-size: 12px;
    line-height: 1.5;
    color: var(--ochre-700, hsl(6 65% 48%));
    background: color-mix(in srgb, var(--ochre-500, hsl(6 65% 55%)) 10%, transparent);
    padding: 6px 10px;
    border-radius: 6px;
  }
  :global(html.dark) .cv-preview,
  :global(html[data-theme-mode="dark"]) .cv-preview {
    background: linear-gradient(180deg, hsl(30 6% 18%), hsl(30 6% 14%));
    border-color: hsl(30 8% 24%);
  }
  :global(html.dark) .cv-url-input,
  :global(html[data-theme-mode="dark"]) .cv-url-input {
    border-color: hsl(30 8% 22%);
    background: hsl(30 6% 16%);
  }
</style>
