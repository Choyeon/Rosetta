/**
 * 全站统一动效快捷入口
 * ---------------------
 * 提供页面常用动效组合方法，避免在各页面重复书写 transition class。
 * 所有动画 CSS 定义在 assets/css/main.css 中（@layer components）。
 */

/** 页面 transition 配置：配合 <Transition name="page-fade" mode="out-in"> 使用 */
export const pageTransition = {
  name: 'page-fade',
  mode: 'out-in' as const,
  appear: true
}

/**
 * 元素进场：生成 animate-in + stagger 组合 class
 * 用法：<div :class="staggerIn(1)">...</div>
 */
export const staggerIn = (order = 0, extra = '') => {
  const steps = ['stagger-1', 'stagger-2', 'stagger-3', 'stagger-4', 'stagger-5', 'stagger-6']
  const step = steps[Math.max(0, Math.min(order, steps.length - 1))]
  return ['animate-in', step, extra].filter(Boolean).join(' ')
}

/**
 * 滚动显现快捷 class 组合
 * 用法：<div :class="reveal()">进入视口会自动淡入上移</div>
 */
export const reveal = (extra = '') => {
  return ['scroll-reveal', extra].filter(Boolean).join(' ')
}

/**
 * 卡片 Hover 抬升快捷 class
 */
export const cardLift = (extra = '') => {
  return ['lift-hover', 'rounded-xl', 'border', 'border-border', 'bg-card', 'shadow-sm', extra].filter(Boolean).join(' ')
}

/**
 * 统一滚动显现 + 阅读进度 + TOC 激活联动
 * 全部基于 IntersectionObserver + window scroll 事件，无额外依赖
 */

/**
 * useScrollReveal：给带 .scroll-reveal 的元素加 IntersectionObserver
 * 用法：在 layout 或页面 onMounted 里调一次 useScrollReveal() 即可
 *       组件 class 里加 .scroll-reveal 就行，进入视口自动加 is-visible
 */
export const useScrollReveal = (rootSelector = 'body') => {
  if (!import.meta.client) return { observe: () => {}, unobserveAll: () => {} }

  let observer: IntersectionObserver | null = null
  const observedEls = new WeakSet<Element>()

  const start = () => {
    if (observer) return
    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            observer?.unobserve(entry.target)
          }
        }
      },
      { rootMargin: '0px 0px -48px 0px', threshold: 0.12 }
    )
    const root = document.querySelector(rootSelector) ?? document.body
    root.querySelectorAll<HTMLElement>('.scroll-reveal').forEach(el => observe(el))
  }

  const observe = (el: Element | null | undefined) => {
    if (!el || observedEls.has(el)) return
    if (!observer) start()
    observer?.observe(el)
    observedEls.add(el)
  }

  const unobserveAll = () => {
    observer?.disconnect()
    observer = null
  }

  onMounted(start)
  onBeforeUnmount(unobserveAll)

  return { observe, unobserveAll }
}

/**
 * useReadingProgress：页面顶部阅读进度条（文章详情页用）
 * 返回 0~100 的百分比 ref，直接绑定 style.width
 */
export const useReadingProgress = (scope = () => document.documentElement) => {
  if (!import.meta.client) {
    return { progress: ref(0), reset: () => {} }
  }
  const progress = ref(0)
  let raf = 0

  const compute = () => {
    const el = typeof scope === 'function' ? scope() : scope
    if (!el) return
    const scrollTop = window.scrollY || document.documentElement.scrollTop || 0
    // 文章容器：用 window 整体滚动（因为 sticky header 是全局的）
    const docHeight = document.documentElement.scrollHeight - window.innerHeight
    progress.value = docHeight > 0 ? Math.max(0, Math.min(100, (scrollTop / docHeight) * 100)) : 0
  }

  const onScroll = () => {
    if (raf) return
    raf = requestAnimationFrame(() => {
      compute()
      raf = 0
    })
  }

  const reset = () => {
    progress.value = 0
    window.scrollTo({ top: 0, behavior: 'instant' })
    compute()
  }

  onMounted(() => {
    compute()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('resize', onScroll)
    if (raf) cancelAnimationFrame(raf)
  })

  return { progress, reset }
}

/**
 * TOC 工具：从一段 HTML（渲染后的 Markdown）里提取所有 h1~h3 生成目录
 *            并返回当前激活项的 id（scroll-spy 联动）
 * 注：调用需在 nextTick 后，或 v-html 渲染完成后。
 */
export interface TocItem {
  id: string
  text: string
  level: 1 | 2 | 3 | 4
  offsetTop: number
}

const slugify = (text: string, existing: Set<string>): string => {
  let base = text
    .toLowerCase()
    .trim()
    .replace(/[\s]+/g, '-')
    .replace(/[^\p{Letter}\p{Number}-]/gu, '')
  if (!base) base = 'section'
  let id = base
  let i = 1
  while (existing.has(id)) id = `${base}-${++i}`
  existing.add(id)
  return id
}

export const extractTOC = (container: HTMLElement | null): TocItem[] => {
  if (!container) return []
  const headings = container.querySelectorAll<HTMLHeadingElement>('h1, h2, h3, h4')
  const items: TocItem[] = []
  const used = new Set<string>()
  headings.forEach((h) => {
    if (!h.id) h.id = slugify(h.textContent || '', used)
    items.push({
      id: h.id,
      text: (h.textContent || '').trim(),
      level: Number(h.tagName[1]) as TocItem['level'],
      offsetTop: Math.round(h.getBoundingClientRect().top + window.scrollY - 88)
    })
  })
  return items
}

export const useTOCScrollSpy = (items: () => TocItem[]) => {
  if (!import.meta.client) {
    return { activeId: ref<string | null>(null), scrollTo: (_id: string) => {} }
  }
  const activeId = ref<string | null>(null)
  let raf = 0

  const update = () => {
    const list = items()
    if (!list.length) return
    const scroll = window.scrollY + 100
    let current: TocItem | null = null
    for (const it of list) {
      if (it.offsetTop <= scroll) current = it
      else break
    }
    if (!current && list.length) current = list[0] ?? null
    if (current && activeId.value !== current.id) activeId.value = current.id
  }

  const onScroll = () => {
    if (raf) return
    raf = requestAnimationFrame(() => {
      update()
      raf = 0
    })
  }

  const scrollTo = (id: string) => {
    const el = document.getElementById(id)
    if (!el) return
    const y = el.getBoundingClientRect().top + window.scrollY - 80
    window.scrollTo({ top: y, behavior: 'smooth' })
    // 手动设置，避免滚动动画期间 activeId 闪烁
    activeId.value = id
    if (history.replaceState) {
      history.replaceState(null, '', `#${id}`)
    }
  }

  onMounted(() => {
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('resize', onScroll)
    if (raf) cancelAnimationFrame(raf)
  })

  return { activeId, scrollTo }
}

/**
 * 字数 & 阅读时长计算（中文按字符，英文按词，中文约 380 字/分钟，英文约 220 wpm）
 */
export const estimateReadingStats = (plainText: string, locale = 'zh') => {
  const clean = (plainText || '').trim()
  if (!clean) return { chars: 0, words: 0, minutes: 1 }

  // 把 Markdown code fence / HTML 标签清掉，粗略估算
  const stripped = clean
    .replace(/```[\s\S]*?```/g, '  ')
    .replace(/`[^`]*`/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/[#>*_~\-+|]+/g, ' ')

  const cjkCount = (stripped.match(/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/gu) || []).length
  const nonCjk = stripped.replace(/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/gu, ' ')
  const wordCount = nonCjk.split(/\s+/).filter(Boolean).length

  const chars = stripped.replace(/\s+/g, '').length
  // 估算阅读分钟：
  const isCjkReader = ['zh', 'zh_Hant', 'ja', 'ko'].includes(String(locale || 'zh'))
  const cjkCpm = 380 // 中文 / 日韩语读者 CJK 字符 / 分钟
  const latinWpm = 220
  const minutes = Math.max(
    1,
    Math.round(
      (isCjkReader ? cjkCount / cjkCpm : 0) + wordCount / latinWpm + (isCjkReader ? 0 : cjkCount / (cjkCpm * 0.6))
    )
  )
  return { chars, words: wordCount + cjkCount, minutes }
}
