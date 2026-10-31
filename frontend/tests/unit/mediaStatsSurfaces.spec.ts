/**
 * 媒体库统计的四段对账（批次 #152）。
 *
 * `GET /api/media/library/stats` 里的 `type_stats` 带 count + size 两个维度，而 `MediaStatsData`
 * 同时挂了一组只为旧页面兼容的分类型计数别名——**体积（size）只有 type_stats 给得出**，
 * 此前前台一个点都没读，于是后台永远答不出「哪种格式吃掉多少空间」。
 * 同批退役 `total_size_formatted`：后端自己算了一遍人类可读体积，而前台全部走
 * `lib/utils::formatBytes`，同一页面出现两种口径（1.0 MB / 1.00 MB）就是双真相。
 *
 * 钉住：后端投影的键 ⊇ 前端 type 声明的键 ⊇ 模板真正读走的键；`type_stats` 必须有真实消费点；
 * 退役族（`total_size_formatted` / `format_file_size`）在前后端与文档里都不许复活。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const backendMedia = readFileSync(join(REPO, 'backend', 'api', 'media.py'), 'utf-8')
const referenceDoc = readFileSync(join(REPO, 'backend', 'docs', 'api_reference.md'), 'utf-8')
const endpointsDoc = readFileSync(join(REPO, 'backend', 'docs', 'api_endpoints.md'), 'utf-8')
const manage = readFileSync(join(ROOT, 'composables', 'useAdminManage.ts'), 'utf-8')
const library = readFileSync(join(ROOT, 'pages', 'admin', 'media', 'library.vue'), 'utf-8')

/** Python 类体里声明的字段名（四空格缩进的 `name: type`） */
function pyFields(body: string): string[] {
  return [...body.matchAll(/^ {4}([A-Za-z_]\w*)\s*:/gm)].map(m => m[1]!)
}

/** TS interface 体里声明的键名（两空格缩进；doc 注释行以 `*` 起头，不会误命中） */
function tsFields(body: string): string[] {
  return [...body.matchAll(/^ {2}([A-Za-z_]\w*)\s*:/gm)].map(m => m[1]!)
}

function pyClass(name: string, source: string): string {
  const head = `class ${name}`
  const start = source.indexOf(head)
  expect(start, `后端缺少 ${name}`).toBeGreaterThan(-1)
  const rest = source.slice(start + head.length)
  const next = rest.search(/^class /m)
  return next === -1 ? rest : rest.slice(0, next)
}

function tsInterface(name: string, source: string): string {
  const head = `export interface ${name} {`
  const start = source.indexOf(head)
  expect(start, `前端缺少 interface ${name}`).toBeGreaterThan(-1)
  const rest = source.slice(start + head.length)
  const end = rest.indexOf('\n}')
  expect(end, `interface ${name} 没有收口的 \n}`).toBeGreaterThan(-1)
  return rest.slice(0, end)
}

const backendStatsFields = pyFields(pyClass('MediaStatsData', backendMedia))
const frontendStatsFields = tsFields(tsInterface('AdminMediaStats', manage))

describe('media library stats surfaces', () => {
  it('backend projects type_stats with both count and size', () => {
    expect(backendStatsFields).toEqual(
      expect.arrayContaining(['total_count', 'total_size', 'type_stats'])
    )
    const typeStatFields = pyFields(pyClass('MediaTypeStat', backendMedia))
    expect(typeStatFields).toEqual(['count', 'size'])
    expect(backendMedia).toContain('"type_stats": type_statistics')
  })

  it('frontend row type declares no key the backend does not project', () => {
    expect(frontendStatsFields.length).toBeGreaterThan(0)
    for (const key of frontendStatsFields) {
      expect(backendStatsFields, `前端 AdminMediaStats.${key} 在后端没有投影`).toContain(key)
    }
  })

  it('type_stats is declared with a real consumer reading its size', () => {
    expect(manage).toMatch(/type_stats:\s*Record<string,\s*\{ count: number, size: number \}>/)
    expect(library).toContain('Object.entries(stats.value.type_stats)')
    expect(library).toContain('stat.size')
    expect(library).toContain('formatSize(stat.size)')
    expect(library).toContain('{{ row.sizeText }}')
  })

  it('every file_type the backend can store has a label', () => {
    const block = backendMedia.slice(
      backendMedia.indexOf('LIBRARY_TYPE_EXTENSIONS: dict'),
      backendMedia.indexOf('LIBRARY_ALLOWED_EXTENSIONS')
    )
    expect(block.length).toBeGreaterThan(0)
    const storedTypes = [...block.matchAll(/^ {4}"(\w+)":/gm)].map(m => m[1]!)
    expect(storedTypes.length).toBeGreaterThan(0)
    // 兜底档：_file_type_for_ext 落在白名单外时写 other
    storedTypes.push('other')
    const labelBlock = library.slice(
      library.indexOf('const TYPE_STAT_LABELS'),
      library.indexOf('const typeStatRows')
    )
    expect(labelBlock.length).toBeGreaterThan(0)
    for (const t of storedTypes) {
      expect(labelBlock, `file_type "${t}" 在后台没有中文名`).toMatch(
        new RegExp(`^\\s*${t}: `, 'm')
      )
    }
  })

  it('retired formatted-size family stays dead', () => {
    for (const source of [backendMedia, manage, library, referenceDoc, endpointsDoc]) {
      expect(source).not.toContain('total_size_formatted')
    }
    expect(backendMedia).not.toContain('format_file_size')
  })
})
