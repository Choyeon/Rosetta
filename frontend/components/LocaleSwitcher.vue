<script setup lang="ts">
import { Globe } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator
} from '~~/components/ui/dropdown-menu'
import { useI18n } from 'vue-i18n'

const { t, locale, setLocale } = useI18n()

interface LocaleOption {
  code: string
  name: string
  nativeName: string
<<<<<<< Updated upstream
}

const displayLocales: LocaleOption[] = [
  { code: 'zh', name: 'Chinese (Simplified)', nativeName: '简体中文' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
  { code: 'zh_Hant', name: 'Chinese (Traditional)', nativeName: '繁體中文' }
=======
  /** ISO 3166-1 alpha-2 country code for flag-icons library */
  flag: string
}

const displayLocales: LocaleOption[] = [
  { code: 'zh', name: 'Chinese (Simplified)', nativeName: '简体中文', flag: 'cn' },
  { code: 'en', name: 'English', nativeName: 'English', flag: 'us' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', flag: 'jp' },
  { code: 'zh_Hant', name: 'Chinese (Traditional)', nativeName: '繁體中文', flag: 'tw' }
>>>>>>> Stashed changes
]

const resolveName = (code: string) => {
  const hit = displayLocales.find((l) => l.code === code)
  return hit?.nativeName || code
}

<<<<<<< Updated upstream
const handleSetLocale = async (code: string) => {
  await setLocale(code)
=======
const flagOf = (code: string) =>
  displayLocales.find((l) => l.code === code)?.flag || 'un'

const handleSetLocale = async (code: string) => {
  await setLocale(code as "zh"|"en"|"ja"|"zh_Hant")
>>>>>>> Stashed changes
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
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
<<<<<<< Updated upstream
      <Button variant="ghost" size="icon" :aria-label="t('common.language') || '语言'">
        <Globe class="h-[1.2rem] w-[1.2rem]" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-48">
      <DropdownMenuLabel>{{ t('common.language') || '语言' }}</DropdownMenuLabel>
=======
      <Button
        variant="ghost"
        size="icon"
        :aria-label="t('common.language') || 'Language'"
        class="relative"
      >
        <span
          class="fi rounded-sm"
          :class="`fi-${flagOf(locale as string)}`"
          :title="resolveName(locale as string)"
          style="font-size: 18px; line-height: 1;"
          aria-hidden="true"
        />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-56">
      <DropdownMenuLabel class="flex items-center gap-2">
        <Globe class="size-3.5 text-muted-foreground" />
        {{ t('common.language') || 'Language' }}
      </DropdownMenuLabel>
>>>>>>> Stashed changes
      <DropdownMenuSeparator />
      <DropdownMenuGroup>
        <DropdownMenuItem
          v-for="loc in displayLocales"
          :key="loc.code"
<<<<<<< Updated upstream
          :class="locale === loc.code ? 'bg-accent text-accent-foreground' : ''"
          @click="handleSetLocale(loc.code)"
        >
          {{ resolveName(loc.code) }}
=======
          :class="[
            'flex items-center gap-3 cursor-pointer',
            locale === loc.code ? 'bg-accent text-accent-foreground' : ''
          ]"
          @click="handleSetLocale(loc.code)"
        >
          <span
            class="fi rounded-sm shrink-0"
            :class="`fi-${loc.flag}`"
            style="font-size: 20px; line-height: 1;"
            aria-hidden="true"
          />
          <span class="flex flex-col min-w-0">
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
>>>>>>> Stashed changes
        </DropdownMenuItem>
      </DropdownMenuGroup>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
