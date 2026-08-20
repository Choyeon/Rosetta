<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Separator } from '~~/components/ui/separator'
import type { Category } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'

const { t, locale, setLocale } = useI18n()

const currentYear = new Date().getFullYear()

interface FooterLink {
  labelKey: string
  to?: string
  href?: string
}

const { data: categories } = await useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `footer:categories:${locale.value}`,
  default: () => []
})

const pickLocalized = (value: string | Record<string, string>): string => {
  if (typeof value === 'string') return value
  return value[locale.value] || value.zh || Object.values(value)[0] || ''
}

const categoryLinks = computed<FooterLink[]>(() => (categories.value || []).map(category => ({
  labelKey: pickLocalized(category.name),
  to: `/posts?category=${encodeURIComponent(category.slug)}`
})))

const resourceLinks: FooterLink[] = [
  { labelKey: 'footer.linkRSS', href: '/rss.xml' },
  { labelKey: 'footer.linkSitemap', href: '/sitemap.xml' },
  { labelKey: 'footer.linkRepo', href: 'https://github.com/ChuyuChoyeon/Rosetta' }
]

const quickLocales = [
  { code: 'zh', label: '简体中文', flag: 'cn' },
  { code: 'en', label: 'English', flag: 'us' },
  { code: 'ja', label: '日本語', flag: 'jp' },
  { code: 'zh_Hant', label: '繁體中文', flag: 'tw' }
]

const handleSetLocale = async (code: string) => {
  await setLocale(code as 'zh' | 'en' | 'ja' | 'zh_Hant')
  try {
    if (import.meta.client) {
      document.cookie = `i18n_redirected=${code}; path=/; max-age=31536000; SameSite=Lax`
    }
  } catch {
    /* ignore */
  }
}
</script>

<template>
  <footer class="border-t bg-muted/30">
    <div class="container mx-auto py-12 md:py-16">
      <div class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-12">
        <!-- Brand column -->
        <div class="lg:col-span-4">
          <NuxtLink
            to="/"
            class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight mb-4"
          >
            <img
              src="/logo/rosetta-monochrome-icon.png"
              alt="Rosetta"
              class="size-6 h-6 w-6 dark:contrast-0 dark:brightness-200"
              loading="lazy"
              @error="(e: any) => { e.currentTarget.style.display = 'none' }"
            >
            Rosetta
          </NuxtLink>
          <p class="text-sm text-muted-foreground leading-relaxed mb-6 max-w-sm">
            {{ t('footer.description', '穿越语言的边界 · Modern Blog System') }}
          </p>
          <div class="flex items-center gap-2 mb-6">
            <Button
              variant="ghost"
              size="icon"
              as-child
            >
              <a
                href="https://github.com/ChuyuChoyeon/Rosetta"
                target="_blank"
                rel="noreferrer"
                :aria-label="t('footer.githubLabel', 'GitHub')"
              >
                <svg
                  viewBox="0 0 24 24"
                  class="h-4 w-4"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 .587c-6.627 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.776.419-1.305.762-1.605-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23a11.507 11.507 0 013.003-.404c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.896-.015 3.286 0 .315.217.695.825.577 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
              </a>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              as-child
            >
              <a
                href="/rss.xml"
                :aria-label="t('footer.rssLabel', 'RSS')"
              >
                <svg
                  viewBox="0 0 24 24"
                  class="h-4 w-4"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M5 3a1 1 0 00-1 1v2a15 15 0 0115 15h2a1 1 0 001-1A18 18 0 005 3zm0 6a1 1 0 00-1 1v2a9 9 0 019 9h2a1 1 0 001-1A12 12 0 005 9zm2.5 6a2.5 2.5 0 100 5 2.5 2.5 0 000-5z" />
                </svg>
              </a>
            </Button>
          </div>
          <p class="text-xs text-muted-foreground">
            © {{ currentYear }} Rosetta · {{ t('footer.rightsReserved', 'All rights reserved.') }}
          </p>
        </div>

        <!-- Categories -->
        <div class="lg:col-span-2">
          <h4 class="font-bold uppercase tracking-wider text-xs text-muted-foreground mb-4">
            {{ t('footer.categories', 'CATEGORIES') }}
          </h4>
          <ul class="space-y-3">
            <li
              v-for="link in categoryLinks"
              :key="link.to"
            >
              <NuxtLink
                :to="link.to!"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ link.labelKey }}
              </NuxtLink>
            </li>
          </ul>
        </div>

        <!-- Resources -->
        <div class="lg:col-span-3">
          <h4 class="font-bold uppercase tracking-wider text-xs text-muted-foreground mb-4">
            {{ t('footer.resources', 'RESOURCES') }}
          </h4>
          <ul class="space-y-3">
            <li
              v-for="link in resourceLinks"
              :key="link.to || link.href"
            >
              <NuxtLink
                v-if="link.to"
                :to="link.to"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ t(link.labelKey, link.labelKey) }}
              </NuxtLink>
              <a
                v-else
                :href="link.href"
                target="_blank"
                rel="noreferrer"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ t(link.labelKey, link.labelKey) }}
              </a>
            </li>
          </ul>
        </div>
      </div>

      <Separator class="my-10" />

      <div class="flex flex-col md:flex-row justify-between items-center gap-4">
        <!-- Quick locale switch (with flags) -->
        <div class="flex items-center gap-2 flex-wrap">
          <button
            v-for="loc in quickLocales"
            :key="loc.code"
            type="button"
            class="group inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            @click="handleSetLocale(loc.code)"
          >
            <span
              class="fi rounded-sm shrink-0"
              :class="`fi-${loc.flag}`"
              style="font-size: 14px; line-height: 1;"
              aria-hidden="true"
            />
            <span>{{ loc.label }}</span>
          </button>
        </div>
        <div class="text-xs text-muted-foreground text-center md:text-right">
          © {{ currentYear }} Rosetta
        </div>
      </div>
    </div>
  </footer>
</template>
