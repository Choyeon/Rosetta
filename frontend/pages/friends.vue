<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-emerald-100 to-teal-100 dark:from-emerald-900/30 dark:to-teal-900/30 mb-5">
        <Link2 class="size-7 text-success" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('friends.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('friends.desc') }}
      </p>
    </header>

    <div
      v-if="loading"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
    >
      <Skeleton
        v-for="i in 4"
        :key="i"
        class="h-48 rounded-2xl"
      />
    </div>

    <div
      v-else-if="fetchError"
      class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
    >
      {{ t('admin.posts.loadFailed') }}
    </div>

    <div
      v-else-if="friendLinks.length"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"
    >
      <a
        v-for="friend in friendLinks"
        :key="friend.id"
        :href="friend.url"
        :target="friend.target_blank ? '_blank' : undefined"
        :rel="friend.target_blank ? 'noopener noreferrer' : undefined"
      >
        <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden">
          <CardHeader class="p-5 pb-3">
            <div class="flex items-start gap-3 mb-3">
              <div
                class="size-12 shrink-0 rounded-xl flex items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 to-zinc-200 dark:from-slate-800 dark:to-zinc-700 transition-transform duration-300 group-hover:scale-105"
              >
                <img
                  v-if="friend.logo"
                  :src="friend.logo"
                  :alt="friend.name"
                  class="w-full h-full object-cover"
                  loading="lazy"
                >
                <span
                  v-else
                  class="font-display text-lg font-bold text-slate-600 dark:text-slate-300"
                >
                  {{ friend.name?.[0]?.toUpperCase() }}
                </span>
              </div>
              <div class="flex-1 min-w-0">
                <CardTitle class="font-display text-base tracking-tight group-hover:underline underline-offset-4 truncate">
                  {{ friend.name }}
                </CardTitle>
              </div>
            </div>
            <CardDescription class="line-clamp-3 text-sm leading-relaxed min-h-[3.75rem]">
              {{ friend.description || t('friends.noDesc') }}
            </CardDescription>
          </CardHeader>
          <CardFooter class="p-5 pt-0 flex items-center justify-between text-sm border-t mt-2">
            <span class="text-muted-foreground truncate pr-2 max-w-[65%]">
              {{ friend.url?.replace(/^https?:\/\//, '') }}
            </span>
            <div class="inline-flex items-center gap-1 text-success shrink-0">
              {{ t('friends.visit') }}
              <ExternalLink class="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </div>
          </CardFooter>
        </Card>
      </a>
    </div>

    <div
      v-else
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Link2 class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('friends.noLinks') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '~~/components/ui/card'
import { Skeleton } from '~~/components/ui/skeleton'
import { useFriendLinks } from '~~/composables/useCore'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Link2, ExternalLink } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t } = useI18n()

const { getFriendLinks } = useFriendLinks()

const { data: links, pending: loading, error: fetchError } = await getFriendLinks()

const friendLinks = computed(() => links.value ?? [])
</script>
