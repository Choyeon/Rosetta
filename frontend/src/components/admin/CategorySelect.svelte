<script lang="ts">
import { createEventDispatcher } from "svelte";

export interface CategoryOption {
	id: number;
	name: string;
	slug?: string;
	is_active?: boolean;
}

export let categoryId: number | null = null;
export let categories: CategoryOption[] = [];
export let placeholder = "搜索或选择分类";
export let allowClear = true;
export let disabled = false;

const dispatch = createEventDispatcher<{
	change: number | null;
}>();

let inputVal = "";
let listId = `cat-sel-${Math.random().toString(36).slice(2, 9)}`;
let _idToName = new Map<number, string>();

$: {
	_idToName = new Map(categories.map((c) => [c.id, c.name]));
}

$: selectedName = categoryId != null ? (_idToName.get(categoryId) ?? "") : "";

function sync(v: number | null) {
	categoryId = v;
	dispatch("change", v);
}

function pickByNameOrId(val: string) {
	if (!val) {
		if (allowClear) sync(null);
		return;
	}
	// try id first
	const idNum = Number(val);
	if (Number.isFinite(idNum) && categories.some((c) => c.id === idNum)) {
		sync(idNum);
		inputVal = _idToName.get(idNum) ?? val;
		return;
	}
	const found = categories.find(
		(c) => c.name === val || String(c.id) === val || c.slug === val,
	);
	if (found) {
		sync(found.id);
		inputVal = found.name;
	} else if (!allowClear) {
		// keep previous
		inputVal = selectedName;
	} else {
		sync(null);
	}
}

function onBlur() {
	if (inputVal !== selectedName) {
		pickByNameOrId(inputVal.trim());
		if (!categoryId) inputVal = "";
	}
}

function onKeyDown(e: KeyboardEvent) {
	if (disabled) return;
	if (e.key === "Enter") {
		e.preventDefault();
		pickByNameOrId(inputVal.trim());
	} else if (e.key === "Escape") {
		(e.target as HTMLInputElement).blur();
	}
}

function clearSelected(e: Event) {
	e.preventDefault();
	e.stopPropagation();
	if (disabled || !allowClear) return;
	sync(null);
	inputVal = "";
}

$: if (selectedName && !inputVal) inputVal = selectedName;
</script>

<div class="cs-wrap" class:cs-disabled={disabled}>
  <div class="cs-input-row">
    <input
      bind:value={inputVal}
      list={categories.length ? listId : undefined}
      type="text"
      class="cs-input"
      {placeholder}
      {disabled}
      autocomplete="off"
      spellcheck="false"
      on:keydown={onKeyDown}
      on:blur={onBlur}
      on:change={(e) => pickByNameOrId((e.target as HTMLInputElement).value)}
    />
    {#if allowClear && (categoryId != null || inputVal)}
      <button
        type="button"
        class="cs-clear"
        aria-label="清除分类"
        on:mousedown={clearSelected}
        on:touchstart={clearSelected}
        tabindex={disabled ? -1 : 0}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    {/if}
  </div>
  {#if categories.length}
    <datalist id={listId}>
      {#each categories as c (c.id)}
        <option value={c.name} data-id={String(c.id)}>{c.name}</option>
      {/each}
    </datalist>
  {/if}
  {#if !categories.length}
    <div class="cs-empty">暂无分类，请先到「分类管理」创建</div>
  {:else if allowClear}
    <div class="cs-hint">留空或点 × 可设为「未分类」</div>
  {/if}
</div>

<style lang="css">
  .cs-wrap {
    display: flex;
    flex-direction: column;
    gap: 6px;
    width: 100%;
  }
  .cs-wrap.cs-disabled {
    opacity: 0.6;
    pointer-events: none;
  }
  .cs-input-row {
    position: relative;
    width: 100%;
  }
  .cs-input {
    width: 100%;
    height: 32px;
    padding: 4px 30px 4px 11px;
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
  .cs-input:hover {
    border-color: var(--ochre-400, hsl(35 85% 50%));
  }
  .cs-input:focus {
    border-color: var(--ochre-500, hsl(35 85% 50%));
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--ochre-500, hsl(35 85% 50%)) 25%, transparent);
  }
  .cs-input::placeholder {
    color: color-mix(in srgb, var(--walnut-500, hsl(24 10% 45%)) 70%, transparent);
  }
  .cs-clear {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    width: 22px;
    height: 22px;
    border-radius: 9999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--walnut-400, hsl(24 10% 55%));
    cursor: pointer;
    transition: background-color 140ms ease, color 140ms ease;
  }
  .cs-clear:hover {
    background: color-mix(in srgb, var(--walnut-500, hsl(24 10% 45%)) 12%, transparent);
    color: var(--walnut-700, hsl(24 10% 20%));
  }
  .cs-hint,
  .cs-empty {
    font-size: 12px;
    line-height: 1.6;
    color: color-mix(in srgb, var(--walnut-500, hsl(24 10% 45%)) 90%, transparent);
  }
  .cs-empty {
    color: var(--ochre-600, hsl(35 75% 42%));
  }
  :global(html.dark) .cs-input,
  :global(html[data-theme-mode="dark"]) .cs-input {
    border-color: hsl(30 8% 22%);
    background: hsl(30 6% 16%);
  }
</style>
