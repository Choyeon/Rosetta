<script setup lang="ts">
import { Globe } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { useI18n } from 'vue-i18n'

const { t, locale, setLocale } = useI18n()

interface LocaleOption {
  code: string
  name: string
  nativeName: string
  flag: string
}

const displayLocales: LocaleOption[] = [
  { code: 'zh', name: 'Chinese (Simplified)', nativeName: '简体中文', flag: 'cn' },
  { code: 'en', name: 'English', nativeName: 'English', flag: 'us' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', flag: 'jp' },
  { code: 'zh_Hant', name: 'Chinese (Traditional)', nativeName: '繁體中文', flag: 'tw' }
]

const resolveName = (code: string) =>
  displayLocales.find(l => l.code === code)?.nativeName || code

const flagOf = (code: string) =>
  displayLocales.find(l => l.code === code)?.flag || 'un'

const handleSetLocale = async (code: string) => {
  await setLocale(code as 'zh' | 'en' | 'ja' | 'zh_Hant')
  if (!import.meta.client) return
  try {
    document.cookie = 'i18n_redirected=' + code + '; path=/; max-age=31536000; SameSite=Lax'
  } catch { /* ignore */ }
}
</script>

<template>
  <div class="locale-switcher relative inline-flex items-center">
    <Button
      variant="ghost"
      size="icon"
      :aria-label="t('common.language') || 'Language'"
      :title="resolveName(locale as string)"
      class="locale-switcher__trigger"
    >
      <span
        class="fi rounded-sm"
        :class="'fi-' + flagOf(locale as string)"
        style="font-size: 18px; line-height: 1;"
        aria-hidden="true"
      />
    </Button>

    <div
      role="menu"
      :aria-label="t('common.language') || 'Language'"
      class="locale-switcher__menu"
    >
      <div class="flex items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground select-none">
        <Globe class="size-3.5" />
        <span>{{ t('common.language') || 'Language' }}</span>
      </div>
      <div class="h-px bg-border/70 my-1" />
      <ul
        role="listbox"
        class="p-1"
      >
        <li
          v-for="loc in displayLocales"
          :key="loc.code"
          role="option"
          :aria-selected="locale === loc.code"
          :tabindex="locale === loc.code ? 0 : -1"
          class="locale-switcher__item"
          :class="{ 'is-active': locale === loc.code }"
          @click.stop="handleSetLocale(loc.code)"
          @keydown.enter.prevent.stop="handleSetLocale(loc.code)"
          @keydown.space.prevent.stop="handleSetLocale(loc.code)"
        >
          <span
            class="fi rounded-sm shrink-0"
            :class="'fi-' + loc.flag"
            style="font-size: 20px; line-height: 1;"
            aria-hidden="true"
          />
          <span class="flex flex-col min-w-0 flex-1">
            <span class="font-medium leading-tight truncate">{{ loc.nativeName }}</span>
            <span class="text-[11px] text-muted-foreground leading-tight truncate">{{ loc.name }}</span>
          </span>
          <svg
            v-if="locale === loc.code"
            class="ml-auto size-4 shrink-0 text-foreground/80"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fill-rule="evenodd"
              d="M16.704 5.29a1 1 0 010 1.42l-7.5 7.5a1 1 0 01-1.414 0l-3.5-3.5a1 1 0 111.414-1.42L8.5 12.084l6.79-6.794a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
          </svg>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.locale-switcher__menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 14rem;
  z-index: 50;
  border-radius: 0.6rem;
  border: 1px solid hsl(var(--border));
  background-color: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
  box-shadow: var(--card-shadow-lg);
  backdrop-filter: blur(10px);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px) scale(0.98);
  transform-origin: top right;
  transition:
    opacity 160ms cubic-bezier(0.2, 0.8, 0.2, 1),
    transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1),
    visibility 160ms linear;
}

.locale-switcher:hover .locale-switcher__menu,
.locale-switcher:focus-within .locale-switcher__menu,
.locale-switcher__menu:focus-within {
  opacity: 1;
  visibility: visible;
  transform: translateY(0) scale(1);
}

.locale-switcher__item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.45rem 0.55rem;
  border-radius: 0.4rem;
  outline: none;
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}

.locale-switcher__item:hover,
.locale-switcher__item:focus-visible {
  background-color: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
}

.locale-switcher__item.is-active {
  background-color: color-mix(in oklab, hsl(var(--accent)) 70%, transparent);
  color: hsl(var(--accent-foreground));
}

@media (max-width: 640px) {
  .locale-switcher__menu {
    min-width: 13rem;
  }
}
</style>
