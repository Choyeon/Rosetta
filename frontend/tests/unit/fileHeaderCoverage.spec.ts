/**
 * 文件级注释覆盖守卫：扫描 frontend 手写源码，要求每个 .vue / .ts 文件的第一行
 * （模板优先 SFC：或紧邻 `<script` 上方）就是文件级注释块。
 *
 * 为什么用测试来守：注释覆盖靠自觉一定会退化——批量补一轮能盖住全仓，之后新增的
 * 文件又会全部裸奔。这条断言把"新文件必须带文件级说明"变成 CI 硬门禁，
 * 失败信息直接列出缺哪些文件，不必再手工 grep。
 *
 * 排除：components/ui/**（shadcn-vue vendored 原子件，下次 `shadcn add` 会覆盖）、
 * *.d.ts（自动生成）、tests/**（验证代码自身）、public/**（静态资源）。
 */
import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
import process from 'node:process'

const ROOT = process.cwd().replace(/[\\/]$/, '')

/** 整目录跳过：非手写源码，或由工具生成/上游维护 */
const SKIP_DIRS = new Set([
  '.git',
  '.nuxt',
  '.output',
  '.vscode',
  'dist',
  'node_modules',
  'public',
  'tests'
])
const SOURCE_EXTS = ['.vue', '.ts']

function extnameOf(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot)
}

function isCommentLine(line: string): boolean {
  return /^\s*(<!--|\/\*|\/\/)/.test(line)
}

function hasFileHeader(lines: string[]): boolean {
  const first = lines.find(l => l.trim() !== '') ?? ''
  if (isCommentLine(first)) return true
  // 模板优先的 SFC：注释块紧贴 <script> 之前（中间至多一个空行）也算
  const scriptIdx = lines.findIndex(l => /^<script[\s>]/.test(l))
  if (scriptIdx <= 0) return false
  let i = scriptIdx - 1
  if (i >= 0 && (lines[i] ?? '').trim() === '') i--
  return i >= 0 && /^\s*(-->|<!--)/.test(lines[i] ?? '')
}

/** 逐个文件判定"是否有文件级注释"，返回缺失清单（相对 frontend/ 的路径）。 */
function collectFilesWithoutHeader(): string[] {
  const missing: string[] = []
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = `${dir}/${entry.name}`
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) continue
        // vendored shadcn 原子件不要求注释
        if (entry.name === 'ui' && dir.replace(/\\/g, '/').endsWith('/components')) continue
        walk(full)
        continue
      }
      if (!SOURCE_EXTS.includes(extnameOf(entry.name))) continue
      if (entry.name.endsWith('.d.ts')) continue
      if (!hasFileHeader(readFileSync(full, 'utf8').split('\n'))) {
        missing.push(full.slice(ROOT.length + 1).replace(/\\/g, '/'))
      }
    }
  }
  walk(ROOT)
  return missing.sort()
}

describe('前端文件级注释覆盖', () => {
  it('每个手写源码文件都以文件级注释开头', () => {
    // 断言字符串而不是数组：失败时 Vitest 会把缺失文件列表原样端出来
    expect(collectFilesWithoutHeader().join('\n')).toBe('')
  })
})
