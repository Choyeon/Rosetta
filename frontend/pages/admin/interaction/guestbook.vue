<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">
        留言板管理
      </h1>
    </div>

    <Tabs
      v-model="activeTab"
      @update:model-value="onTabChange"
    >
      <TabsList>
        <TabsTrigger value="all">
          全部
        </TabsTrigger>
        <TabsTrigger value="pending">
          待审
        </TabsTrigger>
        <TabsTrigger value="approved">
          已通过
        </TabsTrigger>
        <TabsTrigger value="rejected">
          已拒绝
        </TabsTrigger>
        <TabsTrigger value="spam">
          垃圾
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="all"
        class="mt-6"
      >
        <CommentListContent
          status="all"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="pending"
        class="mt-6"
      >
        <CommentListContent
          status="pending"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="approved"
        class="mt-6"
      >
        <CommentListContent
          status="approved"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="rejected"
        class="mt-6"
      >
        <CommentListContent
          status="rejected"
          :is-guestbook="true"
        />
      </TabsContent>
      <TabsContent
        value="spam"
        class="mt-6"
      >
        <CommentListContent
          status="spam"
          :is-guestbook="true"
        />
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import CommentListContent from './_parts/CommentListContent.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const activeTab = ref('all')
const refreshKey = ref(0)

const onTabChange = () => {
  refreshKey.value++
}

provide('refreshKey', refreshKey)
</script>
