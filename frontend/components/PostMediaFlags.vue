<!--
  列表卡片上的「这篇带音频 / 带视频」指示位（批次 #120）。

  只读列表项的三位存在性（`has_audio` / `has_video` / `has_embed`），**不读地址**：
  媒体地址仍只有详情口回（列表投影里没有那三列），所以这里既不会泄出文件名，
  也不需要再判 CSP/合规——后端写入口已经拦过一遍。
  视频档把 `has_video`（站内视频）与 `has_embed`（YouTube）合成一个位：
  对读者的问题只有一个——「点进去有没有画面」。
-->
<template>
  <span
    v-if="audio || video"
    class="inline-flex items-center gap-2 shrink-0"
  >
    <span
      v-if="audio"
      class="inline-flex items-center"
      :title="t('post.hasAudio')"
    >
      <Music
        class="size-3.5 shrink-0"
        aria-hidden="true"
      />
      <span class="sr-only">{{ t('post.hasAudio') }}</span>
    </span>
    <span
      v-if="video"
      class="inline-flex items-center"
      :title="t('post.hasVideo')"
    >
      <Video
        class="size-3.5 shrink-0"
        aria-hidden="true"
      />
      <span class="sr-only">{{ t('post.hasVideo') }}</span>
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Music, Video } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

interface Props {
  post: {
    has_audio?: boolean
    has_video?: boolean
    has_embed?: boolean
  }
}

const props = defineProps<Props>()
const { t } = useI18n()

const audio = computed(() => !!props.post.has_audio)
const video = computed(() => !!(props.post.has_video || props.post.has_embed))
</script>
