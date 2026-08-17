<template>
  <!-- eslint-disable vue/no-v-html -- 预览 HTML 均经 DOMPurify.sanitize 净化 -->
  <div
    ref="rootRef"
    data-md-editor
    class="md-editor flex flex-col rounded-lg border bg-background overflow-hidden"
    :class="fullscreen ? 'fixed inset-0 z-[70] rounded-none border-0' : ''"
    @drop.prevent="onDrop"
    @dragover.prevent
  >
    <!-- 工具栏 -->
    <div class="flex flex-wrap items-center gap-0.5 border-b bg-muted/40 px-2 py-1.5">
      <Button
        v-for="tool in wrapTools"
        :key="tool.key"
        type="button"
        variant="ghost"
        size="icon-sm"
        class="size-8"
        :title="tool.title"
        :disabled="mode === 'preview'"
        @click="tool.action()"
      >
        <component
          :is="tool.icon"
          class="size-4"
        />
      </Button>

      <Separator
        orientation="vertical"
        class="mx-1 !h-5"
      />

      <Button
        v-for="tool in blockTools"
        :key="tool.key"
        type="button"
        variant="ghost"
        size="icon-sm"
        class="size-8"
        :title="tool.title"
        :disabled="mode === 'preview'"
        @click="tool.action()"
      >
        <component
          :is="tool.icon"
          class="size-4"
        />
      </Button>

      <Separator
        orientation="vertical"
        class="mx-1 !h-5"
      />

      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        class="size-8"
        :title="t('admin.editor.toolbar.image')"
        :disabled="mode === 'preview' || uploading"
        @click="openFilePicker"
      >
        <Loader2
          v-if="uploading"
          class="size-4 animate-spin"
        />
        <ImageIcon
          v-else
          class="size-4"
        />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        class="size-8"
        :title="t('admin.editor.toolbar.link')"
        :disabled="mode === 'preview'"
        @click="insertLink"
      >
        <Link class="size-4" />
      </Button>

      <Separator
        orientation="vertical"
        class="mx-1 !h-5"
      />

      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        class="size-8"
        :title="t('admin.editor.toolbar.undo')"
        :disabled="mode === 'preview' || !canUndo"
        @click="undo"
      >
        <Undo2 class="size-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        class="size-8"
        :title="t('admin.editor.toolbar.redo')"
        :disabled="mode === 'preview' || !canRedo"
        @click="redo"
      >
        <Redo2 class="size-4" />
      </Button>

      <div class="ml-auto flex items-center gap-1">
        <div class="flex items-center rounded-md bg-background border p-0.5">
          <Button
            v-for="m in modeOptions"
            :key="m.value"
            type="button"
            variant="ghost"
            size="sm"
            class="h-7 px-2.5 text-xs"
            :class="mode === m.value ? 'bg-muted' : ''"
            @click="mode = m.value"
          >
            {{ m.label }}
          </Button>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          class="size-8"
          :title="t('admin.editor.toolbar.fullscreen')"
          @click="toggleFullscreen"
        >
          <Minimize2
            v-if="fullscreen"
            class="size-4"
          />
          <Maximize2
            v-else
            class="size-4"
          />
        </Button>
      </div>
    </div>

    <!-- 主体：编辑 / 分屏 / 预览 -->
    <div
      class="flex min-h-0 flex-1 flex-col md:flex-row"
      :style="bodyStyle"
    >
      <textarea
        v-show="mode !== 'preview'"
        ref="textareaRef"
        :value="modelValue"
        :placeholder="placeholder"
        class="md-editor-textarea h-full w-full flex-1 resize-none bg-background p-4 font-mono text-sm leading-relaxed outline-none md:min-w-0"
        :class="mode === 'split' ? 'md:border-r-0' : ''"
        spellcheck="false"
        @input="onInput"
        @keydown="onKeydown"
        @paste="onPaste"
        @click="updateCaret"
        @keyup="updateCaret"
        @select="updateCaret"
      />
      <div
        v-if="mode !== 'edit'"
        class="md-preview h-full w-full flex-1 overflow-y-auto border-t p-4 md:border-t-0 md:border-l"
        :class="mode === 'split' ? 'md:border-l' : ''"
        v-html="renderedHtml"
      />
    </div>

    <!-- 状态栏 -->
    <div class="flex items-center justify-between border-t bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
      <span>{{ t('admin.editor.wordCount', { n: charCount }) }}</span>
      <span>{{ uploading ? t('admin.editor.uploading') : `${caret.line}:${caret.col}` }}</span>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      multiple
      class="hidden"
      @change="onFileSelected"
    >
  </div>
</template>

<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Separator } from '~~/components/ui/separator'
import {
  Bold,
  Italic,
  Heading2,
  Heading3,
  Quote,
  Code,
  SquareCode,
  List,
  ListOrdered,
  Minus,
  Link,
  Image as ImageIcon,
  Undo2,
  Redo2,
  Maximize2,
  Minimize2,
  Loader2
} from '@lucide/vue'
import { Marked } from 'marked'
import DOMPurify from 'dompurify'
import { apiFetch } from '~~/composables/useAPI'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  height?: number | string
}>(), {
  placeholder: '',
  height: 480
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'save'): void
}>()

const { t } = useI18n()
const toast = useToast()

const rootRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

type EditorMode = 'edit' | 'split' | 'preview'
const mode = ref<EditorMode>('split')
const fullscreen = ref(false)
const uploading = ref(false)
const caret = ref({ line: 1, col: 1 })

const modeOptions = computed(() => [
  { value: 'edit' as EditorMode, label: t('admin.editor.mode.edit') },
  { value: 'split' as EditorMode, label: t('admin.editor.mode.split') },
  { value: 'preview' as EditorMode, label: t('admin.editor.mode.preview') }
])

const bodyStyle = computed(() => {
  if (fullscreen.value) return {}
  const h = typeof props.height === 'number' ? `${props.height}px` : props.height
  return { height: h }
})

/* ==================== 预览渲染（marked + DOMPurify） ==================== */

const mdRenderer = new Marked({ gfm: true, breaks: false })

const renderedHtml = computed(() => {
  if (!props.modelValue) return ''
  // DOMPurify 依赖浏览器 DOM；SSR 侧返回空串，避免 Node 侧崩溃
  if (import.meta.server) return ''
  try {
    return DOMPurify.sanitize(mdRenderer.parse(props.modelValue) as string)
  } catch {
    return DOMPurify.sanitize(props.modelValue)
  }
})

/* ==================== 字数 / 光标位置 ==================== */

const charCount = computed(() => {
  const text = props.modelValue || ''
  // 中文（含假名）按字符计数，其余按单词计数
  const cjk = (text.match(/[\u4e00-\u9fa5\u3040-\u30ff\uff00-\uffef]/g) || []).length
  const words = (text.replace(/[\u4e00-\u9fa5\u3040-\u30ff\uff00-\uffef]/g, ' ').match(/[a-zA-Z0-9]+/g) || []).length
  return cjk + words
})

function updateCaret() {
  const ta = textareaRef.value
  if (!ta) return
  const pos = ta.selectionStart ?? 0
  const before = ta.value.slice(0, pos)
  const lines = before.split('\n')
  caret.value = { line: lines.length, col: pos - before.lastIndexOf('\n') }
}

/* ==================== 历史（撤销 / 重做） ==================== */

const historyPast = ref<string[]>([])
const historyFuture = ref<string[]>([])
let lastRecordAt = 0

const canUndo = computed(() => historyPast.value.length > 0)
const canRedo = computed(() => historyFuture.value.length > 0)

function recordHistory(prev: string, coalesce = false) {
  const now = Date.now()
  // 输入事件按 800ms 窗口合并，避免每个字符占据一条历史
  if (coalesce && now - lastRecordAt < 800) {
    lastRecordAt = now
    return
  }
  lastRecordAt = now
  historyPast.value.push(prev)
  if (historyPast.value.length > 200) historyPast.value.shift()
  historyFuture.value = []
}

function undo() {
  if (!historyPast.value.length) return
  historyFuture.value.push(props.modelValue)
  const prev = historyPast.value.pop()!
  emit('update:modelValue', prev)
  lastRecordAt = 0
}

function redo() {
  if (!historyFuture.value.length) return
  historyPast.value.push(props.modelValue)
  const next = historyFuture.value.pop()!
  emit('update:modelValue', next)
  lastRecordAt = 0
}

/* ==================== 编辑操作 ==================== */

function onInput(e: Event) {
  const ta = e.target as HTMLTextAreaElement
  recordHistory(props.modelValue, true)
  emit('update:modelValue', ta.value)
  updateCaret()
}

/** 在指定区间替换文本并恢复焦点与选区 */
function applyEdit(start: number, end: number, replacement: string, selStart?: number, selEnd?: number) {
  const ta = textareaRef.value
  const value = props.modelValue ?? ''
  const next = value.slice(0, start) + replacement + value.slice(end)
  emit('update:modelValue', next)
  if (import.meta.client) {
    nextTick(() => {
      if (!ta) return
      ta.focus()
      const s = selStart ?? start + replacement.length
      const e2 = selEnd ?? s
      ta.setSelectionRange(s, e2)
      updateCaret()
    })
  }
}

function wrapSelection(before: string, after: string, placeholderText: string) {
  const ta = textareaRef.value
  if (!ta) return
  recordHistory(props.modelValue)
  const { selectionStart: s, selectionEnd: e } = ta
  const selected = ta.value.slice(s, e)
  if (selected) {
    applyEdit(s, e, `${before}${selected}${after}`)
  } else {
    applyEdit(s, e, `${before}${placeholderText}${after}`, s + before.length, s + before.length + placeholderText.length)
  }
}

/** 行首前缀切换（引用 / 列表） */
function toggleLinePrefix(prefix: string) {
  const ta = textareaRef.value
  if (!ta) return
  recordHistory(props.modelValue)
  const value = ta.value
  const { selectionStart: s, selectionEnd: e } = ta
  const lineStart = value.lastIndexOf('\n', s - 1) + 1
  const lineEndIdx = value.indexOf('\n', e)
  const lineEnd = lineEndIdx === -1 ? value.length : lineEndIdx
  const block = value.slice(lineStart, lineEnd)
  const lines = block.split('\n')
  const allPrefixed = lines.every(l => l.startsWith(prefix))
  const next = lines
    .map(l => (allPrefixed ? l.slice(prefix.length) : prefix + l))
    .join('\n')
  applyEdit(lineStart, lineEnd, next, lineStart, lineStart + next.length)
}

function insertBlock(text: string) {
  const ta = textareaRef.value
  if (!ta) return
  recordHistory(props.modelValue)
  const { selectionStart: s } = ta
  const atLineStart = s === 0 || ta.value[s - 1] === '\n'
  const prefix = atLineStart ? '' : '\n'
  applyEdit(s, s, `${prefix}${text}`)
}

function insertLink() {
  const ta = textareaRef.value
  if (!ta) return
  const { selectionStart: s, selectionEnd: e } = ta
  const selected = ta.value.slice(s, e)
  const looksLikeUrl = /^(https?:\/\/|\/)/i.test(selected.trim())
  recordHistory(props.modelValue)
  if (looksLikeUrl) {
    applyEdit(s, e, `[${t('admin.editor.linkText')}](${selected.trim()})`)
  } else if (selected) {
    applyEdit(s, e, `[${selected}](https://)`, s + selected.length + 3, s + selected.length + 11)
  } else {
    applyEdit(s, e, `[${t('admin.editor.linkText')}](https://)`, s + 1, s + 1 + t('admin.editor.linkText').length)
  }
}

function indentSelection() {
  const ta = textareaRef.value
  if (!ta) return
  const value = ta.value
  const { selectionStart: s, selectionEnd: e } = ta
  if (s !== e && value.slice(s, e).includes('\n')) {
    toggleIndent(true)
    return
  }
  recordHistory(props.modelValue)
  applyEdit(s, s, '  ')
}

function toggleIndent(add: boolean) {
  const ta = textareaRef.value
  if (!ta) return
  recordHistory(props.modelValue)
  const value = ta.value
  const { selectionStart: s, selectionEnd: e } = ta
  const lineStart = value.lastIndexOf('\n', s - 1) + 1
  const lineEndIdx = value.indexOf('\n', e)
  const lineEnd = lineEndIdx === -1 ? value.length : lineEndIdx
  const lines = value.slice(lineStart, lineEnd).split('\n')
  let deltaFirst = 0
  let deltaTotal = 0
  const next = lines
    .map((l, i) => {
      if (add) {
        const d = 2
        if (i === 0) deltaFirst = d
        deltaTotal += d
        return `  ${l}`
      }
      const removed = l.match(/^ {1,2}/)
      const d = removed ? removed[0].length : 0
      if (i === 0) deltaFirst = -d
      deltaTotal -= d
      return l.slice(d)
    })
    .join('\n')
  applyEdit(lineStart, lineEnd, next, Math.max(lineStart, s + deltaFirst), Math.max(lineStart, e + deltaTotal))
}

/* ==================== 图片上传（按钮 / 粘贴 / 拖拽） ==================== */

const UPLOAD_PLACEHOLDER_RE = /!\[([^\]]*)上传中[^\]]*\]\(\)/g

function openFilePicker() {
  fileInputRef.value?.click()
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  uploadImages(files)
}

function onPaste(e: ClipboardEvent) {
  const files = Array.from(e.clipboardData?.files || [])
  if (files.some(f => f.type.startsWith('image/'))) {
    e.preventDefault()
    uploadImages(files)
  }
}

function onDrop(e: DragEvent) {
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) uploadImages(files)
}

async function uploadImages(files: File[]) {
  const images = files.filter(f => f.type.startsWith('image/'))
  if (!images.length) return
  uploading.value = true
  try {
    for (const file of images) {
      await uploadOne(file)
    }
  } finally {
    uploading.value = false
  }
}

async function uploadOne(file: File) {
  if (import.meta.client) {
    const ta = textareaRef.value
    if (ta) {
      const pos = ta.selectionEnd ?? ta.value.length
      recordHistory(props.modelValue)
      applyEdit(pos, pos, `\n![${t('admin.editor.uploading')}]()\n`)
    }
  }
  try {
    const formData = new FormData()
    formData.append('file', file)
    // 后端 POST /api/media/upload，字段名 file，返回 { url, filename, width, height }
    const res = await apiFetch<{ url?: string } & Record<string, unknown>>('/media/upload', {
      method: 'POST',
      body: formData
    })
    const url = res?.url || (res as { data?: { url?: string } })?.data?.url
    if (!url) throw new Error('upload response missing url')
    replaceUploadPlaceholder(`![${file.name}](${url})`)
  } catch (err) {
    console.error('[MarkdownEditor] image upload failed:', err)
    replaceUploadPlaceholder('')
    toast.error(t('admin.editor.uploadFailed'))
  }
}

function replaceUploadPlaceholder(replacement: string) {
  const value = props.modelValue ?? ''
  const matches = [...value.matchAll(UPLOAD_PLACEHOLDER_RE)]
  const last = matches[matches.length - 1]
  if (!last) return
  const start = last.index ?? 0
  const next = value.slice(0, start) + replacement + value.slice(start + last[0].length)
  emit('update:modelValue', next)
}

/* ==================== 快捷键 ==================== */

function onKeydown(e: KeyboardEvent) {
  const mod = e.ctrlKey || e.metaKey
  if (mod && !e.shiftKey && !e.altKey) {
    const key = e.key.toLowerCase()
    if (key === 'b') {
      e.preventDefault()
      wrapSelection('**', '**', t('admin.editor.boldText'))
      return
    }
    if (key === 'i') {
      e.preventDefault()
      wrapSelection('*', '*', t('admin.editor.italicText'))
      return
    }
    if (key === 'k') {
      e.preventDefault()
      insertLink()
      return
    }
    if (key === 's') {
      // 阻止浏览器保存对话框；save 事件由页面级监听统一触发（见 PostForm）
      e.preventDefault()
      emit('save')
      return
    }
  }
  if (e.key === 'Tab') {
    e.preventDefault()
    if (e.shiftKey) toggleIndent(false)
    else indentSelection()
    return
  }
  if (e.key === 'Escape' && fullscreen.value) {
    fullscreen.value = false
  }
}

function toggleFullscreen() {
  fullscreen.value = !fullscreen.value
}

/* ==================== 工具栏定义 ==================== */

const wrapTools = computed(() => [
  { key: 'bold', icon: Bold, title: `${t('admin.editor.toolbar.bold')} (Ctrl+B)`, action: () => wrapSelection('**', '**', t('admin.editor.boldText')) },
  { key: 'italic', icon: Italic, title: `${t('admin.editor.toolbar.italic')} (Ctrl+I)`, action: () => wrapSelection('*', '*', t('admin.editor.italicText')) },
  { key: 'h2', icon: Heading2, title: t('admin.editor.toolbar.heading2'), action: () => toggleLinePrefix('## ') },
  { key: 'h3', icon: Heading3, title: t('admin.editor.toolbar.heading3'), action: () => toggleLinePrefix('### ') }
])

const blockTools = computed(() => [
  { key: 'quote', icon: Quote, title: t('admin.editor.toolbar.quote'), action: () => toggleLinePrefix('> ') },
  { key: 'inlineCode', icon: Code, title: t('admin.editor.toolbar.inlineCode'), action: () => wrapSelection('`', '`', t('admin.editor.codeText')) },
  { key: 'codeBlock', icon: SquareCode, title: t('admin.editor.toolbar.codeBlock'), action: () => insertBlock('```\n' + t('admin.editor.codeText') + '\n```\n') },
  { key: 'ul', icon: List, title: t('admin.editor.toolbar.unorderedList'), action: () => toggleLinePrefix('- ') },
  { key: 'ol', icon: ListOrdered, title: t('admin.editor.toolbar.orderedList'), action: () => toggleLinePrefix('1. ') },
  { key: 'hr', icon: Minus, title: t('admin.editor.toolbar.divider'), action: () => insertBlock('\n---\n') }
])
</script>

<style scoped>
.md-editor-textarea {
  tab-size: 2;
}

/* 编辑器预览的轻量 markdown 样式（与前台 prose-shadcn 视觉对齐） */
.md-preview :deep(h1),
.md-preview :deep(h2),
.md-preview :deep(h3),
.md-preview :deep(h4) {
  font-weight: 600;
  margin-top: 1.25em;
  margin-bottom: 0.6em;
  line-height: 1.35;
}
.md-preview :deep(h1) { font-size: 1.6rem; }
.md-preview :deep(h2) { font-size: 1.35rem; }
.md-preview :deep(h3) { font-size: 1.15rem; }
.md-preview :deep(h4) { font-size: 1.05rem; }
.md-preview :deep(p) { margin: 0.75em 0; line-height: 1.8; }
.md-preview :deep(a) {
  color: hsl(var(--primary));
  text-decoration: underline;
  text-underline-offset: 3px;
}
.md-preview :deep(ul),
.md-preview :deep(ol) {
  padding-left: 1.5em;
  margin: 0.75em 0;
}
.md-preview :deep(ul) { list-style: disc; }
.md-preview :deep(ol) { list-style: decimal; }
.md-preview :deep(li) { margin: 0.3em 0; }
.md-preview :deep(blockquote) {
  border-left: 2px solid hsl(var(--muted-foreground) / 0.4);
  padding-left: 1em;
  margin: 0.75em 0;
  color: hsl(var(--muted-foreground));
}
.md-preview :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.875em;
  background: hsl(var(--muted));
  border-radius: 4px;
  padding: 0.15em 0.4em;
}
.md-preview :deep(pre) {
  background: hsl(var(--muted));
  border-radius: 8px;
  padding: 1em;
  overflow-x: auto;
  margin: 0.75em 0;
}
.md-preview :deep(pre code) {
  background: transparent;
  padding: 0;
}
.md-preview :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 0.5em 0;
}
.md-preview :deep(hr) {
  border: none;
  border-top: 1px solid hsl(var(--border));
  margin: 1.5em 0;
}
.md-preview :deep(table) {
  border-collapse: collapse;
  margin: 0.75em 0;
  width: 100%;
}
.md-preview :deep(th),
.md-preview :deep(td) {
  border: 1px solid hsl(var(--border));
  padding: 0.4em 0.75em;
  text-align: left;
}
</style>
