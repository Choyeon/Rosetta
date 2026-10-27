<!--
  后台 Markdown 编辑器：工具栏快捷键 + 撤销/重做历史栈 + 图片粘贴/拖拽上传 + 分屏预览。
  硬契约：预览 v-html 必须走 marked + lib/sanitize 白名单净化（与前台文章链路同一条），
  禁止退回旧自制正则渲染器——它不处理引号与 URL scheme，javascript: 可直达后台预览（XSS）；
  onPaste 挂在 document 级（onMounted 注册 / onBeforeUnmount 移除），本组件仅限 client-only 场景使用。
-->
<script setup lang="ts">
import { useVModel } from '@vueuse/core'
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { Marked } from 'marked'
import { useMediaUpload } from '~~/composables/useMedia'
import { useToast } from '~~/composables/useToast'
import { sanitizeMarkdownHtml } from '~~/lib/sanitize'
import { Tabs, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Button } from '~~/components/ui/button'
import {
  Image as ImageIcon,
  Link as LinkIcon,
  Undo2,
  Redo2,
  Maximize2,
  Minimize2,
  Bold,
  Italic,
  Heading2,
  Heading3,
  Quote,
  Code,
  Braces,
  List,
  ListOrdered,
  Minus
} from '@lucide/vue'

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
// 默认进入纯编辑：分屏在 700px 级的主栏里会把编辑/预览各压到 350px，
// 长代码行与表格都看不清。切到「分屏 / 预览」只需一次点击。
const mode = ref<'edit' | 'split' | 'preview'>('edit')
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
  historyStack.value.push(content.value || '')
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
    const result = await useMediaUpload(file, 'post')
    if (result?.url) {
      insertAtCursor(`\n![image](${result.url})\n`)
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
    if (!item) continue
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
    if (!file) continue
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

// 预览渲染与前台文章/独立页链路统一：marked 解析 + lib/sanitize 白名单净化。
// 旧自制正则渲染器只转义 <>&，不处理引号与 URL scheme，
// [x](javascript:...) 与 `" onmouseover=` 可直达预览 v-html（后台预览 XSS）。
const mdPreview = new Marked({ gfm: true, breaks: true })

const previewHtml = computed(() => {
  const md = content.value || ''
  if (!md.trim()) return ''
  try {
    return sanitizeMarkdownHtml(mdPreview.parse(md) as string)
  } catch {
    return ''
  }
})

onMounted(() => {
  historyStack.value = [content.value || '']
  historyIndex.value = 0
  document.addEventListener('paste', onPaste as unknown as EventListener)
})

onBeforeUnmount(() => {
  document.removeEventListener('paste', onPaste as unknown as EventListener)
  if (historyTimer) clearTimeout(historyTimer)
})

type ToolbarBtn = {
  key: string
  title: string
  label?: string
  cls?: string
  icon?: typeof ImageIcon
}

const toolbarButtons: ToolbarBtn[] = [
  { key: 'bold', icon: Bold, title: '粗体 (Ctrl+B)' },
  { key: 'italic', icon: Italic, title: '斜体 (Ctrl+I)' },
  { key: 'h2', icon: Heading2, title: '二级标题' },
  { key: 'h3', icon: Heading3, title: '三级标题' },
  { key: 'quote', icon: Quote, title: '引用' },
  { key: 'code', icon: Code, title: '行内代码' },
  { key: 'codeblock', icon: Braces, title: '代码块' },
  { key: 'ul', icon: List, title: '无序列表' },
  { key: 'ol', icon: ListOrdered, title: '有序列表' },
  { key: 'hr', icon: Minus, title: '分割线' },
  { key: 'image', icon: ImageIcon, title: '插入图片' },
  { key: 'link', icon: LinkIcon, title: '插入链接 (Ctrl+K)' },
  { key: 'undo', icon: Undo2, title: '撤销 (Ctrl+Z)' },
  { key: 'redo', icon: Redo2, title: '重做 (Ctrl+Y)' }
]

/** 工具栏分组：组间画细分割线，避免 13 个图标挤成一片 */
const toolbarGroups = computed(() => {
  const groups: ToolbarBtn[][] = []
  const boundaries = [2, 4, 7, 10, 12]
  let start = 0
  for (const end of boundaries) {
    groups.push(toolbarButtons.slice(start, end))
    start = end
  }
  groups.push(toolbarButtons.slice(start))
  return groups
})
</script>

<template>
  <div
    class="card-surface no-glow flex flex-col text-card-foreground overflow-hidden"
    :class="{ 'fixed inset-4 z-50 shadow-2xl': isFullscreen }"
  >
    <div class="flex flex-wrap items-center justify-between gap-y-2 border-b border-border px-3 py-2 bg-muted/30">
      <div class="flex min-w-0 flex-wrap items-center gap-0.5">
        <template
          v-for="(group, gi) in toolbarGroups"
          :key="gi"
        >
          <div
            v-if="gi > 0"
            class="mx-1 h-5 w-px bg-border"
          />
          <Button
            v-for="btn in group"
            :key="btn.key"
            type="button"
            variant="ghost"
            size="icon-sm"
            :title="btn.title"
            :aria-label="btn.title"
            class="rounded-[10px] text-muted-foreground hover:text-foreground"
            @click="handleToolbarAction(btn.key)"
          >
            <component
              :is="btn.icon"
              v-if="btn.icon"
              data-icon="inline-start"
            />
            <span
              v-else
              :class="btn.cls"
            >{{ btn.label }}</span>
          </Button>
        </template>
      </div>
      <div class="ml-auto flex items-center gap-2">
        <Tabs
          :model-value="mode"
          class="w-auto"
          @update:model-value="mode = $event as 'edit' | 'split' | 'preview'"
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
          <Minimize2
            v-if="isFullscreen"
            data-icon="inline-start"
          />
          <Maximize2
            v-else
            data-icon="inline-start"
          />
        </Button>
      </div>
    </div>

    <div
      class="flex-1 flex flex-col xl:flex-row overflow-hidden"
      :class="{ 'min-h-[500px]': !isFullscreen, 'h-full': isFullscreen }"
    >
      <div
        v-show="mode !== 'preview'"
        class="flex-1 min-h-[260px] flex flex-col"
        :class="{ 'border-b xl:border-b-0 xl:border-r border-border': mode === 'split' }"
        @drop="onDrop"
        @dragover="onDragOver"
      >
        <textarea
          ref="textareaRef"
          v-model="content"
          :placeholder="placeholder || '开始写点什么...'"
          class="flex-1 w-full resize-none p-4 bg-card text-sm font-mono leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
          @keydown="onKeyDown"
          @input="updateCursorPos"
          @click="updateCursorPos"
          @keyup="updateCursorPos"
        />
      </div>

      <div
        v-show="mode !== 'edit'"
        class="flex-1 min-h-[260px] overflow-auto p-5 bg-card"
      >
        <div
          ref="previewRef"
          class="prose-shadcn admin-md-preview max-w-none text-foreground"
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

<style scoped>
/* 预览区使用与前台一致的 .prose-shadcn 排版；但后台分屏很窄，
   前台的 h1 clamp(2.25rem…) 会把标题撑得比编辑器还大，所以这里按
   「文档预览」而不是「文章首屏」的尺度重排一遍。 */
.admin-md-preview {
  max-width: none;
  font-size: 0.9rem;
  line-height: 1.7;
}
.admin-md-preview :deep(h1) {
  font-size: 1.5rem;
  margin: 1.25rem 0 0.75rem;
  line-height: 1.25;
}
.admin-md-preview :deep(h2) {
  font-size: 1.2rem;
  margin: 1.25rem 0 0.6rem;
  line-height: 1.3;
}
.admin-md-preview :deep(h3) {
  font-size: 1.05rem;
  margin: 1rem 0 0.5rem;
}
.admin-md-preview :deep(h4) {
  font-size: 0.95rem;
  margin: 0.9rem 0 0.4rem;
}
.admin-md-preview :deep(p) {
  margin: 0.75rem 0;
}
.admin-md-preview :deep(ul),
.admin-md-preview :deep(ol) {
  margin: 0.75rem 0;
}
.admin-md-preview :deep(pre) {
  margin: 1rem 0;
  padding: 0.9rem 1rem;
}
.admin-md-preview :deep(blockquote) {
  margin: 1rem 0;
}
.admin-md-preview :deep(img) {
  margin: 0.75rem 0;
  border-radius: 0.6rem;
}
.admin-md-preview :deep(table) {
  margin: 1rem 0;
}
</style>
