<!--
  列表卡片上的「这篇要访问密码」指示位（批次 #139）。

  读的是列表族新增的存在性位 `is_password_protected`（后端 `bool(Post.password)`），
  **不读密码本身**：哈希从不进列表载荷，前端也拿不到。
  此前只有详情页知道自己被锁（`is_password_protected` + 闸门页），前台八个卡片渲染面
  一个信号都没有——读者的实际体验是「卡片写着预计 4 分钟，点进去要密码」，
  而「这篇要不要密码」本来就是决定点不点进去的信息。
  与 PostMediaFlags 同形：图标 + `title` + `sr-only`，不新增四语文案键。
-->
<template>
  <span
    v-if="locked"
    class="inline-flex items-center shrink-0"
    :title="t('post.requiresPassword')"
  >
    <Lock
      class="size-3.5 shrink-0"
      aria-hidden="true"
    />
    <span class="sr-only">{{ t('post.requiresPassword') }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Lock } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

interface Props {
  post: {
    is_password_protected?: boolean | null
  }
}

const props = defineProps<Props>()
const { t } = useI18n()

/** 键缺失（旧缓存载荷）按"不锁"处理：宁可不显示提示，也不给公开文章贴一个假闸门。 */
const locked = computed(() => props.post.is_password_protected === true)
</script>
