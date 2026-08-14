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
}

const displayLocales: LocaleOption[] = [
  { code: 'zh', name: 'Chinese (Simplified)', nativeName: '简体中文' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
  { code: 'zh_Hant', name: 'Chinese (Traditional)', nativeName: '繁體中文' }
]

const resolveName = (code: string) => {
  const hit = displayLocales.find((l) => l.code === code)
  return hit?.nativeName || code
}

const handleSetLocale = async (code: string) => {
  await setLocale(code)
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
      <Button variant="ghost" size="icon" :aria-label="t('common.language') || '语言'">
        <Globe class="h-[1.2rem] w-[1.2rem]" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-48">
      <DropdownMenuLabel>{{ t('common.language') || '语言' }}</DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuGroup>
        <DropdownMenuItem
          v-for="loc in displayLocales"
          :key="loc.code"
          :class="locale === loc.code ? 'bg-accent text-accent-foreground' : ''"
          @click="handleSetLocale(loc.code)"
        >
          {{ resolveName(loc.code) }}
        </DropdownMenuItem>
      </DropdownMenuGroup>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
