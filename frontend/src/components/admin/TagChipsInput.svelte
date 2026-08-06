<script lang="ts">
import { createEventDispatcher } from "svelte";

export let tags: string[] = [];
export let suggestions: string[] = [];
export let placeholder = "输入标签后回车添加，逗号分隔";
export let disabled = false;

const dispatch = createEventDispatcher<{
	change: string[];
}>();

let inputEl: HTMLInputElement | null = null;
let inputVal = "";
let chipsId = `tag-chips-${Math.random().toString(36).slice(2, 9)}`;
let listId = `tag-suggest-${Math.random().toString(36).slice(2, 9)}`;

function sync(v: string[]) {
	tags = v;
	dispatch("change", v);
}

function addFromInput(raw?: string) {
	const v = (raw ?? inputVal).trim();
	if (!v) return;
	const parts = v
		.split(/[,，\n]/)
		.map((s) => s.trim())
		.filter(Boolean);
	if (!parts.length) return;
	const next = [...tags];
	for (const p of parts) {
		if (!next.includes(p)) next.push(p);
	}
	sync(next);
	inputVal = "";
}

function removeAt(i: number) {
	const next = [...tags];
	next.splice(i, 1);
	sync(next);
}

function onKeyDown(e: KeyboardEvent) {
	if (disabled) return;
	const key = e.key;
	if (key === "Enter" || key === "," || key === "，") {
		e.preventDefault();
		addFromInput();
		return;
	}
	if (key === "Backspace" && !inputVal && tags.length) {
		e.preventDefault();
		removeAt(tags.length - 1);
	}
}

function onBlur() {
	if (inputVal.trim()) addFromInput();
}

function onPaste(e: ClipboardEvent) {
	const txt = e.clipboardData?.getData("text");
	if (txt && /[,，\n]/.test(txt)) {
		e.preventDefault();
		addFromInput(txt);
	}
}

$: {
	// keep two-way bind companion in sync
	tags = tags ?? [];
}
</script>

<div class="tci-wrap" id={chipsId} class:tci-disabled={disabled}>
  <div class="tci-chips" role="list" aria-label="已选标签">
    {#each tags as t, i (t + i)}
      <span
        class="tci-chip"
        role="listitem"
        tabindex={disabled ? -1 : 0}
        on:click={() => !disabled && removeAt(i)}
        on:keydown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === "Delete" || e.key === "Backspace")) {
            e.preventDefault();
            removeAt(i);
          }
        }}
        title="点击移除"
      >
        <span class="tci-chip-text">{t}</span>
        <svg class="tci-chip-x" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </span>
    {/each}
  </div>
  <div class="tci-input-row">
    <input
      bind:this={inputEl}
      bind:value={inputVal}
      list={suggestions?.length ? listId : undefined}
      type="text"
      class="tci-input"
      {placeholder}
      {disabled}
      autocomplete="off"
      spellcheck="false"
      on:keydown={onKeyDown}
      on:blur={onBlur}
      on:paste={onPaste}
    />
    {#if suggestions?.length}
      <datalist id={listId}>
        {#each suggestions as s (s)}
          <option value={s} />
        {/each}
      </datalist>
    {/if}
  </div>
</div>

<style lang="css">
  .tci-wrap {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .tci-wrap.tci-disabled {
    opacity: 0.6;
    pointer-events: none;
  }
  .tci-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-height: 0;
  }
  .tci-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px 2px 10px;
    height: 24px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--indigo-600, hsl(240 55% 42%));
    background: color-mix(in srgb, var(--indigo-500, hsl(240 60% 50%)) 10%, transparent);
    border: none;
    box-shadow: none;
    cursor: pointer;
    transition: background-color 140ms ease, color 140ms ease, filter 140ms ease;
    transform: none;
    user-select: none;
  }
  .tci-chip:hover {
    background: color-mix(in srgb, var(--indigo-500, hsl(240 60% 50%)) 18%, transparent);
    color: var(--indigo-700, hsl(240 45% 42%));
  }
  .tci-chip:active {
    filter: brightness(0.94);
  }
  .tci-chip:focus-visible {
    outline: 2px solid color-mix(in srgb, var(--indigo-500, hsl(240 60% 50%)) 60%, transparent);
    outline-offset: 1px;
  }
  .tci-chip-text {
    line-height: 20px;
    max-width: 22ch;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tci-chip-x {
    flex-shrink: 0;
    opacity: 0.75;
  }
  .tci-input-row {
    width: 100%;
  }
  .tci-input {
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
  .tci-input:hover {
    border-color: var(--ochre-400, hsl(35 85% 50%));
  }
  .tci-input:focus {
    border-color: var(--ochre-500, hsl(35 85% 50%));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--ochre-500, hsl(35 85% 50%)) 25%, transparent);
  }
  .tci-input::placeholder {
    color: color-mix(in srgb, var(--walnut-500, hsl(24 10% 45%)) 70%, transparent);
  }
  @media (prefers-color-scheme: dark) {
    :global(html[data-theme-mode="dark"]) .tci-input {
      border-color: hsl(30 8% 22%);
      background: hsl(30 6% 16%);
    }
  }
  :global(html.dark) .tci-input {
    border-color: hsl(30 8% 22%);
    background: hsl(30 6% 16%);
  }
</style>
