<!--
  顶栏语言下拉（DropdownMenuRadioGroup 受控于当前 locale）。
  语言持久位只有一枚：rosetta_lang —— 只给前端 locale-prefix.global.client.ts 按它
  给裸路径补语言前缀；接口返回的语言一律由 URL 前缀决定（lang 参数 + Accept-Language），
  后端不读这枚 cookie。（@nuxtjs/i18n 自带的浏览器语言检测已在 nuxt.config 关闭，
  所以不再写它约定的 i18n_redirected。）
  策略：prefix_except_default —— 中文裸路径 /，其它三语 /en /ja /zh_Hant 前缀。
  切换必须"setLocale + 跳到同页的目标语言 URL"两步都做，只 setLocale 会让内容换了
  语言、地址栏仍是默认语言路径，与 canonical/hreflang 的判定互相矛盾。
-->
<script setup lang="ts">
import { Globe, Check, ChevronDown } from '~~/lib/lucide-svg-icons'
import { useI18n } from 'vue-i18n'
import { applyLocalePrefix } from '~~/composables/useSeo'
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
const route = useRoute()
const router = useRouter()

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
  if (code === locale.value) return
  // 先切 i18n 内部状态（影响 useI18n 输出），再跳目标语言的等价路径。
  await setLocale(code as LocaleOption['code'])
  if (!import.meta.client) return
  try {
    document.cookie = 'rosetta_lang=' + code + '; path=/; max-age=31536000; SameSite=Lax'
  } catch { /* ignore */ }
  // 用当前 fullPath（保留 path/query/hash）换目标语言路径。不走 @nuxtjs/i18n 的
  // switchLocalePath()：它按路由名解析，而本仓 i18n 没有 per-locale 自定义路径，
  // "默认语言裸路径 + 其余挂 /code 前缀"就是策略全貌（口径见 useSeo 的
  // applyLocalePrefix——详情页的 /posts/{中文 slug} 在 localePath 下实测会
  // 产出非字符串，同一个解析坑会让切换按钮跳到 [object Object]）。
  const next = applyLocalePrefix(route.fullPath, code)
  if (next && next !== route.fullPath) {
    await router.push(next)
  }
}
</script>

<template>
  <!-- reka-ui DropdownMenu 服务端只渲染空注释占位、客户端渲染触发器 button，
       裸写进 SSR 会让每个用到本组件的页面（顶栏、/oobe 向导顶栏）都报 hydration node mismatch。
       服务端本来也拿不到任何可爬的链接（选项都在展开态的 Content 里），所以这里隔离不损 SEO。 -->
  <ClientOnly>
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
  </ClientOnly>
</template>
