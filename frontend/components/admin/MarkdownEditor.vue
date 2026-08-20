<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { useVModel } from '@vueuse/core'
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useMediaUpload } from '~~/composables/useMedia'
import { useToast } from '~~/composables/useToast'
import { Tabs, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Button } from '~~/components/ui/button'

const props = defineProps<{
  modelValue?: string
  placeholder?: string
}>()

const emits = defineEmits<{
  'update:modelValue': [value: string]
}>()

const content = useVModel(props, 'modelValue', emits, {
  passive: true,
  defaultValue: ''
})

const toast = useToast()
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const previewRef = ref<HTMLDivElement | null>(null)
const mode = ref<'edit' | 'split' | 'preview'>('split')
const isFullscreen = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const historyStack = ref<string[]>([])
const historyIndex = ref(-1)
const historyMaxSize = 50
const cursorLine = ref(1)
const cursorCol = ref(1)

const wordCount = computed(() => {
  const text = content.value || ''
  const chars = text.replace(/\s/g, '').length
  const words = text.split(/\s+/).filter(w => w.length > 0).length
  return { chars, words }
})

const pushHistory = () => {
  if (historyIndex.value < historyStack.value.length - 1) {
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
  }
  historyStack.value.push(content.value)
  if (historyStack.value.length > historyMaxSize) {
    historyStack.value.shift()
  }
  historyIndex.value = historyStack.value.length - 1
}

let historyTimer: ReturnType<typeof setTimeout> | null = null
watch(content, () => {
  if (historyTimer) clearTimeout(historyTimer)
  historyTimer = setTimeout(() => {
    if (historyStack.value[historyIndex.value] !== content.value) {
      pushHistory()
    }
  }, 800)
})

const undo = () => {
  if (historyIndex.value > 0) {
    historyIndex.value--
    content.value = historyStack.value[historyIndex.value]
  }
}

const redo = () => {
  if (historyIndex.value < historyStack.value.length - 1) {
    historyIndex.value++
    content.value = historyStack.value[historyIndex.value]
  }
}

const getSelection = () => {
  const ta = textareaRef.value
  if (!ta) return { start: 0, end: 0, selected: '' }
  return {
    start: ta.selectionStart,
    end: ta.selectionEnd,
    selected: ta.value.substring(ta.selectionStart, ta.selectionEnd)
  }
}

const setSelection = (start: number, end: number) => {
  nextTick(() => {
    const ta = textareaRef.value
    if (!ta) return
    ta.focus()
    ta.setSelectionRange(start, end)
  })
}

const wrapSelection = (before: string, after = before, placeholder = '') => {
  const ta = textareaRef.value
  if (!ta) return
  const { start, end, selected } = getSelection()
  const insertText = selected || placeholder
  const newText
    = ta.value.substring(0, start) + before + insertText + after + ta.value.substring(end)
  content.value = newText
  const newCursor = start + before.length + insertText.length
  setSelection(start + before.length, newCursor)
}

const prefixSelection = (prefix: string) => {
  const ta = textareaRef.value
  if (!ta) return
  const { start, end } = getSelection()
  const textBefore = ta.value.substring(0, start)
  const textAfter = ta.value.substring(end)

  const lineStart = textBefore.lastIndexOf('\n') + 1
  const actualStart = lineStart
  const beforeLines = ta.value.substring(0, actualStart)

  const targetText = ta.value.substring(actualStart, end)
  const lines = targetText.split('\n').map(l => prefix + l).join('\n')

  content.value = beforeLines + lines + textAfter
  setSelection(beforeLines.length, beforeLines.length + lines.length)
}

const insertAtCursor = (text: string, moveCursor = text.length) => {
  const ta = textareaRef.value
  if (!ta) return
  const { start, end } = getSelection()
  content.value = ta.value.substring(0, start) + text + ta.value.substring(end)
  setSelection(start + moveCursor, start + moveCursor)
}

const handleToolbarAction = (action: string) => {
  switch (action) {
    case 'bold':
      wrapSelection('**', '**', '粗体文字')
      break
    case 'italic':
      wrapSelection('*', '*', '斜体文字')
      break
    case 'h2':
      prefixSelection('## ')
      break
    case 'h3':
      prefixSelection('### ')
      break
    case 'quote':
      prefixSelection('> ')
      break
    case 'code':
      wrapSelection('`', '`', 'code')
      break
    case 'codeblock':
      wrapSelection('\n```\n', '\n```\n', 'code block')
      break
    case 'ul':
      prefixSelection('- ')
      break
    case 'ol':
      prefixSelection('1. ')
      break
    case 'hr':
      insertAtCursor('\n---\n')
      break
    case 'image':
      fileInputRef.value?.click()
      break
    case 'link': {
      const sel = getSelection()
      const linkText = sel.selected || '链接文字'
      insertAtCursor(`[${linkText}](url)`)
      nextTick(() => {
        const ta = textareaRef.value
        if (!ta) return
        const urlStart = ta.value.indexOf('](url', getSelection().start - 1)
        if (urlStart !== -1) {
          setSelection(urlStart + 2, urlStart + 5)
        }
      })
      break
    }
    case 'undo':
      undo()
      break
    case 'redo':
      redo()
      break
  }
}

const uploadImageFile = async (file: File) => {
  if (!file.type.startsWith('image/')) {
    toast.error('请上传图片文件')
    return
  }
  try {
    const { data, error } = await useMediaUpload(file, 'post')
    if (error.value) throw error.value
    if (data.value?.url) {
      insertAtCursor(`\n![image](${data.value.url})\n`)
      toast.success('图片上传成功')
    } else {
      toast.error('图片上传失败')
    }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '图片上传失败')
  }
}

const onImageSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) uploadImageFile(file)
  input.value = ''
}

const onPaste = async (e: ClipboardEvent) => {
  const items = e.clipboardData?.items
  if (!items) return
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file) await uploadImageFile(file)
      return
    }
  }
}

const onDrop = async (e: DragEvent) => {
  e.preventDefault()
  const files = e.dataTransfer?.files
  if (!files) return
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    if (file.type.startsWith('image/')) {
      await uploadImageFile(file)
    }
  }
}

const onDragOver = (e: DragEvent) => {
  e.preventDefault()
}

const updateCursorPos = () => {
  const ta = textareaRef.value
  if (!ta) return
  const pos = ta.selectionStart
  const before = ta.value.substring(0, pos)
  cursorLine.value = before.split('\n').length
  const lastNl = before.lastIndexOf('\n')
  cursorCol.value = lastNl === -1 ? pos + 1 : pos - lastNl
}

const onKeyDown = (e: KeyboardEvent) => {
  const ta = e.target as HTMLTextAreaElement
  if (e.ctrlKey || e.metaKey) {
    if (e.key.toLowerCase() === 'b') {
      e.preventDefault()
      handleToolbarAction('bold')
    } else if (e.key.toLowerCase() === 'i') {
      e.preventDefault()
      handleToolbarAction('italic')
    } else if (e.key.toLowerCase() === 'k') {
      e.preventDefault()
      handleToolbarAction('link')
    } else if (e.key.toLowerCase() === 's') {
      pushHistory()
    } else if (e.key.toLowerCase() === 'z' && !e.shiftKey) {
      e.preventDefault()
      undo()
    } else if ((e.key.toLowerCase() === 'z' && e.shiftKey) || e.key.toLowerCase() === 'y') {
      e.preventDefault()
      redo()
    }
  }
  if (e.key === 'Tab') {
    e.preventDefault()
    const { start, end } = getSelection()
    content.value = ta.value.substring(0, start) + '  ' + ta.value.substring(end)
    setSelection(start + 2, start + 2)
  }
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

const simpleMarkdownToHtml = (md: string): string => {
  if (!md) return ''
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-muted p-3 rounded-lg overflow-x-auto my-3 text-sm"><code>$1</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="bg-muted px-1.5 py-0.5 rounded text-sm">$1</code>')
  html = html.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold mt-5 mb-3">$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-6 mb-4">$1</h1>')
  html = html.replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-muted-foreground/20 pl-4 italic my-3 opacity-80">$1</blockquote>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="max-w-full h-auto rounded-lg my-3" />')
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="text-primary underline hover:opacity-80">$1</a>')
  html = html.replace(/^- (.+)$/gm, '<li class="ml-5 list-disc">$1</li>')
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="ml-5 list-decimal">$1</li>')
  html = html.replace(/^---$/gm, '<hr class="my-4 border-border" />')
  html = html.split(/\n\n+/).map((para) => {
    if (/^<(h|pre|blockquote|ul|ol|hr|li|img)/.test(para)) return para
    return `<p class="my-3 leading-relaxed">${para.replace(/\n/g, '<br/>')}</p>`
  }).join('\n')
  return html
}

const previewHtml = computed(() => simpleMarkdownToHtml(content.value || ''))

onMounted(() => {
  historyStack.value = [content.value || '']
  historyIndex.value = 0
  document.addEventListener('paste', onPaste as EventListener)
})

onBeforeUnmount(() => {
  document.removeEventListener('paste', onPaste as EventListener)
  if (historyTimer) clearTimeout(historyTimer)
})

const toolbarButtons = [
  { key: 'bold', label: 'B', title: '粗体 (Ctrl+B)', cls: 'font-bold' },
  { key: 'italic', label: 'I', title: '斜体 (Ctrl+I)', cls: 'italic' },
  { key: 'h2', label: 'H2', title: '二级标题', cls: 'text-xs font-bold' },
  { key: 'h3', label: 'H3', title: '三级标题', cls: 'text-xs font-bold' },
  { key: 'quote', label: '"', title: '引用', cls: '' },
  { key: 'code', label: '`', title: '行内代码', cls: 'font-mono' },
  { key: 'codeblock', label: '```', title: '代码块', cls: 'font-mono text-xs' },
  { key: 'ul', label: 'UL', title: '无序列表', cls: 'text-xs' },
  { key: 'ol', label: 'OL', title: '有序列表', cls: 'text-xs' },
  { key: 'hr', label: '---', title: '分割线', cls: 'text-xs' },
  { key: 'image', label: '🖼', title: '插入图片', cls: '' },
  { key: 'link', label: '🔗', title: '插入链接 (Ctrl+K)', cls: '' },
  { key: 'undo', label: '⟲', title: '撤销 (Ctrl+Z)', cls: '' },
  { key: 'redo', label: '⟳', title: '重做 (Ctrl+Y)', cls: 'scale-x-[-1] inline-block' }
]
</script>

<template>
  <div
    class="card-surface flex flex-col text-card-foreground overflow-hidden"
    :class="{ 'fixed inset-4 z-50 shadow-2xl': isFullscreen }"
  >
    <div class="flex items-center justify-between border-b border-border px-3 py-2 bg-muted/30">
      <div class="flex flex-wrap items-center gap-1">
        <template
          v-for="(btn, idx) in toolbarButtons"
          :key="btn.key"
        >
          <Button
            v-if="idx !== toolbarButtons.length - 2"
            type="button"
            variant="ghost"
            size="icon-sm"
            :title="btn.title"
            class="rounded-[12px]"
            @click="handleToolbarAction(btn.key)"
          >
            <span :class="btn.cls">{{ btn.label }}</span>
          </Button>
          <div
            v-else
            class="flex items-center gap-1"
          >
            <div class="w-px h-5 bg-border mx-1" />
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              :title="btn.title"
              class="rounded-[12px]"
              @click="handleToolbarAction(btn.key)"
            >
              <span :class="btn.cls">{{ btn.label }}</span>
            </Button>
          </div>
        </template>
      </div>
      <div class="flex items-center gap-2">
        <Tabs
          :model-value="mode"
          class="w-auto"
          @update:model-value="mode = $event as any"
        >
          <TabsList class="h-8 rounded-[12px]">
            <TabsTrigger
              value="edit"
              class="h-7 text-xs px-3 rounded-[10px]"
            >
              编辑
            </TabsTrigger>
            <TabsTrigger
              value="split"
              class="h-7 text-xs px-3 rounded-[10px]"
            >
              分屏
            </TabsTrigger>
            <TabsTrigger
              value="preview"
              class="h-7 text-xs px-3 rounded-[10px]"
            >
              预览
            </TabsTrigger>
          </TabsList>
        </Tabs>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          class="rounded-[12px]"
          :title="isFullscreen ? '退出全屏' : '全屏'"
          @click="toggleFullscreen"
        >
          <span class="text-sm">{{ isFullscreen ? '✕' : '⛶' }}</span>
        </Button>
      </div>
    </div>

    <div
      class="flex-1 flex overflow-hidden"
      :class="{ 'min-h-[500px]': !isFullscreen, 'h-full': isFullscreen }"
    >
      <div
        v-show="mode !== 'preview'"
        class="flex-1 flex flex-col"
        :class="{ 'border-r border-border': mode === 'split' }"
        @drop="onDrop"
        @dragover="onDragOver"
      >
        <textarea
          ref="textareaRef"
          v-model="content"
          :placeholder="placeholder || '开始写点什么...'"
          class="flex-1 w-full resize-none p-4 bg-card text-sm font-mono leading-relaxed focus:outline-none"
          @keydown="onKeyDown"
          @input="updateCursorPos"
          @click="updateCursorPos"
          @keyup="updateCursorPos"
        />
      </div>

      <div
        v-show="mode !== 'edit'"
        class="flex-1 overflow-auto p-5 bg-card"
      >
        <div
          ref="previewRef"
          class="prose prose-sm max-w-none text-foreground"
          v-html="previewHtml"
        />
      </div>
    </div>

    <div class="flex items-center justify-between border-t border-border px-4 py-2 bg-muted/20 text-xs text-muted-foreground">
      <div class="flex items-center gap-4">
        <span>字数：{{ wordCount.chars }}</span>
        <span>词数：{{ wordCount.words }}</span>
      </div>
      <div>
        行 {{ cursorLine }}，列 {{ cursorCol }}
      </div>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      class="hidden"
      @change="onImageSelect"
    >
  </div>
</template>
