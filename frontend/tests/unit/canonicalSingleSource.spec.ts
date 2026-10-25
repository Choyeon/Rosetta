/**
 * canonical 只允许由 composables/useSeo.ts 单源产出（AGENTS §2.3.3 第 3 条）。
 * 页面里再手写一份 `rel: 'canonical'` / `rel="canonical"` 等于同一页两条规范地址，
 * 爬虫会自行挑一条，规范链接图失控；而用 useRequestURL()/请求 Host 拼地址时，
 * Nitro swr 按路径分键不含 Host，一次请求的 Host 会被固化成 TTL 内所有访客的
 * canonical（缓存投毒面）。本测试静态钉死：页面侧出现任何 canonical 字面量即红。
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')

function collectPages(dir = 'pages', acc: string[] = []): string[] {
  for (const entry of readdirSync(resolve(ROOT, dir))) {
    const rel = `${dir}/${entry}`
    if (statSync(resolve(ROOT, rel)).isDirectory()) {
      collectPages(rel, acc)
    }
    else if (entry.endsWith('.vue')) {
      acc.push(rel)
    }
  }
  return acc
}

describe('canonical 单源（useSeo 唯一产出点）', () => {
  it('pages/**/*.vue 里没有任何手写 canonical', () => {
    const hits: string[] = []
    for (const rel of collectPages()) {
      const src = readFileSync(resolve(ROOT, rel), 'utf-8')
      const count = (src.match(/rel: 'canonical'/g) ?? []).length
        + (src.match(/rel="canonical"/g) ?? []).length
      if (count > 0) hits.push(`${rel} (${count})`)
    }
    expect(hits, `以下页面手写了 canonical，请改走 useSeo()：${hits.join(', ')}`).toEqual([])
  })

  it('单源真实现仍在 composables/useSeo.ts（防止整条链路被静默删掉）', () => {
    const useSeo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')
    expect(useSeo).toContain("rel: 'canonical'")
  })
})
