<!--
  评论管理页：按状态 Tab 承载 CommentListContent（status="all|pending|approved|rejected|spam"）。
  契约：本页不持有任何列表状态——TabsContent 只渲染激活项，切 Tab 即挂载新实例并自行首屏请求，父层无需刷新信号。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="评论管理"
      description="审核、回复与管理全站文章评论"
      :icon="MessageSquare"
    />

    <Tabs v-model="activeTab">
      <AdminTabList>
        <AdminTabTrigger
          v-for="tab in COMMENT_TABS"
          :key="tab.value"
          :value="tab.value"
        >
          {{ tab.label }}
        </AdminTabTrigger>
      </AdminTabList>

      <TabsContent
        value="all"
        class="mt-6"
      >
        <CommentListContent status="all" />
      </TabsContent>
      <TabsContent
        value="pending"
        class="mt-6"
      >
        <CommentListContent status="pending" />
      </TabsContent>
      <TabsContent
        value="approved"
        class="mt-6"
      >
        <CommentListContent status="approved" />
      </TabsContent>
      <TabsContent
        value="rejected"
        class="mt-6"
      >
        <CommentListContent status="rejected" />
      </TabsContent>
      <TabsContent
        value="spam"
        class="mt-6"
      >
        <CommentListContent status="spam" />
      </TabsContent>
      <TabsContent
        value="reports"
        class="mt-6"
      >
        <CommentReportsPanel />
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { Tabs, TabsContent } from '~~/components/ui/tabs'
import AdminTabList from '~~/components/admin/AdminTabList.vue'
import AdminTabTrigger from '~~/components/admin/AdminTabTrigger.vue'
import { MessageSquare } from '@lucide/vue'
import CommentListContent from './_parts/CommentListContent.vue'
import CommentReportsPanel from './_parts/CommentReportsPanel.vue'

definePageMeta({ ssr: false, layout: 'admin' })

// TabsContent 只渲染当前激活项：切 tab 会挂载新的列表实例并自行首屏请求，
// 不需要额外的刷新信号。
const COMMENT_TABS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待审' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已拒绝' },
  { value: 'spam', label: '垃圾' },
  { value: 'reports', label: '举报' }
] as const

const activeTab = ref<string>('all')
</script>
