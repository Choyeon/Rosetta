/**
 * 上传大小预检必须跟随站点设置 `media.max_upload_size`（静态 + 行为双向钉住）。
 *
 * 后端早就在消费这个键（api/media.py::_effective_upload_limit / _image_upload_limit），
 * 前台两处却各自写死数字：
 *   - 媒体库 validateUploadFiles 写死 20MB → 管理员调成 50MB 仍被前端按 20MB 拒掉，
 *     调成 5MB 又能把 12MB 的文件传到一半才收 413（进度条白跑）；
 *   - ImageUploadZone 的提示语写死 `maxSize: 20`（没有任何调用方传过这个 prop），
 *     而它上传的图片口默认上限是 10MB → 同一个页面上"单张最大 20MB"配一条 413，
 *     两个互相矛盾的数都自称是本站的上传策略。
 * 两处现在都从 /api/config 的 max_upload_size 取数，兜底常量只在设置缺失时生效。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  MAX_UPLOAD_BYTES,
  resolveUploadLimitBytes,
  validateUploadFiles
} from '~~/composables/useUploadProgress'

const MB = 1024 * 1024

function fakeFile(name: string, sizeBytes: number): File {
  return { name, size: sizeBytes } as unknown as File
}

describe('resolveUploadLimitBytes', () => {
  it('正数按字节采纳（设置里存的就是字节）', () => {
    expect(resolveUploadLimitBytes(5 * MB)).toBe(5 * MB)
    expect(resolveUploadLimitBytes('5242880')).toBe(5 * MB)
  })

  it('缺失 / 0 / 负数 / 非数字一律回落兜底常量，绝不返回 NaN 让预检失效', () => {
    for (const bad of [undefined, null, '', 0, -1, Number.NaN, 'abc', {}]) {
      expect(resolveUploadLimitBytes(bad)).toBe(MAX_UPLOAD_BYTES)
    }
  })
})

describe('validateUploadFiles 的单文件上限', () => {
  it('不传上限时用兜底常量，超过即拒', () => {
    const r = validateUploadFiles([fakeFile('a.png', MAX_UPLOAD_BYTES + 1)])
    expect(r.accepted).toHaveLength(0)
    expect(r.rejected[0]?.reason).toContain(`${MAX_UPLOAD_BYTES / MB} MB`)
  })

  it('管理员调小上限后，拒绝文案报的是设置里的数而不是 20MB', () => {
    const r = validateUploadFiles([fakeFile('a.png', 6 * MB)], { maxBytes: 5 * MB })
    expect(r.rejected[0]?.reason).toBe('文件过大（6 MB > 5 MB）')
  })

  it('管理员调大上限后，原本被误拒的文件放过去', () => {
    const r = validateUploadFiles([fakeFile('a.png', 30 * MB)], { maxBytes: 50 * MB })
    expect(r.accepted).toHaveLength(1)
    expect(r.rejected).toHaveLength(0)
  })

  it('非法配置值不影响判定（回落兜底常量）', () => {
    expect(validateUploadFiles([fakeFile('a.png', 30 * MB)], { maxBytes: 0 }).rejected).toHaveLength(1)
    expect(validateUploadFiles([fakeFile('a.png', 19 * MB)], { maxBytes: Number.NaN }).accepted).toHaveLength(1)
  })

  it('扩展名白名单先于大小判定（未知扩展名不会因为改上限被放行）', () => {
    const r = validateUploadFiles([fakeFile('a.exe', 1024)], { maxBytes: 50 * MB })
    expect(r.rejected[0]?.reason).toContain('不支持的文件类型')
  })
})

describe('消费点接线', () => {
  const library = readFileSync(resolve(process.cwd(), 'pages/admin/media/library.vue'), 'utf8')
  const zone = readFileSync(resolve(process.cwd(), 'components/ImageUploadZone.vue'), 'utf8')

  it('媒体库把 /api/config 的 max_upload_size 传给预检', () => {
    expect(library).toMatch(/resolveUploadLimitBytes\(siteState\.value\.publicConfig\?\.max_upload_size\)/)
    expect(library).toMatch(/validateUploadFiles\(files, \{ maxBytes: uploadMaxBytes\.value \}\)/)
  })

  it('图片上传区的提示与判定共用同一份上限，且不再有写死的 maxSize prop', () => {
    expect(zone).toMatch(/resolveUploadLimitBytes\(siteState\.value\.publicConfig\?\.max_upload_size\)/)
    expect(zone).toMatch(/单张最大 \{\{ limitLabel \}\}/)
    expect(zone).toMatch(/f\.size > limitBytes\.value/)
    expect(zone).not.toMatch(/props\.maxSize/)
    expect(zone).not.toMatch(/maxSize\?:\s*number/)
  })
})
