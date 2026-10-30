<!--
  关键词高亮：把命中片段包成 <mark>，其余原样输出。
  两条硬约束：
  1. 不用 v-html —— 关键词来自地址栏（?q=），拼 HTML 就是一条反射型 XSS 面；
     这里只产出文本节点 + 由 Vue 转义的 <mark> 包裹。
  2. 只按字面匹配（indexOf + toLowerCase），关键词里的 . * ( ) 一律不当正则元字符；
     大小写不敏感，与后端 ILIKE 召回口径一致。
-->
<template>
  <template
    v-for="(part, i) in parts"
    :key="i"
  >
    <mark
      v-if="part.hit"
      class="rounded-sm bg-primary/20 px-0.5 text-inherit"
    >{{ part.text }}</mark>
    <template v-else>
      {{ part.text }}
    </template>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
  keyword: string
}>()

interface Segment {
  text: string
  hit: boolean
}

const parts = computed<Segment[]>(() => {
  const text = props.text || ''
  const keyword = (props.keyword || '').trim()
  if (!keyword || !text) return text ? [{ text, hit: false }] : []

  const needle = keyword.toLowerCase()
  const haystack = text.toLowerCase()
  const out: Segment[] = []
  let cursor = 0
  let idx = haystack.indexOf(needle)
  while (idx !== -1) {
    if (idx > cursor) out.push({ text: text.slice(cursor, idx), hit: false })
    out.push({ text: text.slice(idx, idx + needle.length), hit: true })
    cursor = idx + needle.length
    idx = haystack.indexOf(needle, cursor)
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor), hit: false })
  return out
})
</script>
