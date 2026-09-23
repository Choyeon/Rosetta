<script setup lang="ts">
import { Globe, Check, ChevronDown } from '~~/lib/lucide-svg-icons'
import { useI18n } from 'vue-i18n'
import { Button } from '~~/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem
} from '~~/components/ui/dropdown-menu'

const { t, locale, setLocale } = useI18n()

interface LocaleOption {
  code: 'zh' | 'en' | 'ja' | 'zh_Hant'
  name: string
  nativeName: string
  /** 顶栏触发器用的极简短标签（语言自称，无需国旗图形） */
  short: string
  flag: string
}

const displayLocales: LocaleOption[] = [
  { code: 'zh', name: 'Chinese (Simplified)', nativeName: '简体中文', short: '中文', flag: 'cn' },
  { code: 'en', name: 'English', nativeName: 'English', short: 'EN', flag: 'us' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', short: '日本語', flag: 'jp' },
  { code: 'zh_Hant', name: 'Chinese (Traditional)', nativeName: '繁體中文', short: '繁體', flag: 'tw' }
]

const shortOf = (code: string) =>
  displayLocales.find(l => l.code === code)?.short || '文A'

const handleSetLocale = async (code: string) => {
  await setLocale(code as LocaleOption['code'])
  if (!import.meta.client) return
  try {
    document.cookie = 'rosetta_lang=' + code + '; path=/; max-age=31536000; SameSite=Lax'
    document.cookie = 'i18n_redirected=' + code + '; path=/; max-age=31536000; SameSite=Lax'
  } catch { /* ignore */ }
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button
        variant="ghost"
        size="sm"
        class="gap-1 px-2 text-sm font-medium"
        :aria-label="t('common.language') || 'Language'"
      >
        <span data-locale-short>{{ shortOf(locale as string) }}</span>
        <ChevronDown
          class="size-3.5 opacity-60"
          aria-hidden="true"
        />
      </Button>
    </DropdownMenuTrigger>

    <DropdownMenuContent
      align="end"
      class="w-56"
    >
      <DropdownMenuLabel class="flex items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground">
        <Globe class="size-3.5" />
        <span>{{ t('common.language') || 'Language' }}</span>
      </DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuRadioGroup
        :model-value="locale as string"
        @update:model-value="(v) => handleSetLocale(String(v ?? locale))"
      >
        <DropdownMenuRadioItem
          v-for="loc in displayLocales"
          :key="loc.code"
          :value="loc.code"
          class="gap-3"
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
          <Check
            v-if="locale === loc.code"
            class="ml-auto size-4 shrink-0"
          />
        </DropdownMenuRadioItem>
      </DropdownMenuRadioGroup>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
