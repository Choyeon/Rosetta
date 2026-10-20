/**
 * 上传预检（大小 + 扩展名）必须跟随站点设置，静态与行为双向钉住。
 *
 * 后端早就在消费这些键（api/media.py::_effective_upload_limit / _effective_library_exts /
 * _image_upload_limit），前台却各自写死：
 *   - 媒体库 validateUploadFiles 写死 20MB → 管理员调成 50MB 仍被前端按 20MB 拒掉，
 *     调成 5MB 又能把 12MB 的文件传到一半才收 413（进度条白跑）；
 *   - ImageUploadZone 的提示语写死 `maxSize: 20`（没有任何调用方传过这个 prop），
 *     而它上传的图片口默认上限是 10MB → 同一个页面上"单张最大 20MB"配一条 413，
 *     两个互相矛盾的数都自称是本站的上传策略；
 *   - 扩展名白名单是内置清单的硬编码副本，且 `<input accept>` 也从它派生 → 管理员在
 *     「媒体与上传 · 允许的文件类型」里去掉 svg 后，选择器照样放行、后端回 400。
 * 现在两处都从 /api/config 下发的同名扁平行取数，兜底常量与内置清单只在设置缺失时生效。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  ALLOWED_UPLOAD_EXTENSIONS,
  MAX_UPLOAD_BYTES,
  UPLOAD_LIMIT_CEILING_BYTES,
  UPLOAD_LIMIT_FLOOR_BYTES,
  resolveAllowedExtensions,
  resolveUploadLimitBytes,
  validateUploadFiles
} from '~~/composables/useUploadProgress'
// 拒绝文案里的数字必须与全站字节口径一致，断言直接复用同一个 formatter
import { formatBytes } from '~~/lib/utils'

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

  it('超出服务端安全区间的配置钳到边界（预检报的数必须等于上传口执行的数）', () => {
    expect(resolveUploadLimitBytes(500 * MB)).toBe(UPLOAD_LIMIT_CEILING_BYTES)
    expect(resolveUploadLimitBytes(1024)).toBe(UPLOAD_LIMIT_FLOOR_BYTES)
    // 300MB 配置若不钳，预检会放行并传到一个大文件的一半再收 413
    expect(validateUploadFiles([fakeFile('a.png', 150 * MB)], { maxBytes: 300 * MB }).accepted)
      .toHaveLength(0)
  })
})

describe('validateUploadFiles 的单文件上限', () => {
  it('不传上限时用兜底常量，超过即拒', () => {
    const r = validateUploadFiles([fakeFile('a.png', MAX_UPLOAD_BYTES + 1)])
    expect(r.accepted).toHaveLength(0)
    expect(r.rejected[0]?.reason).toContain(formatBytes(MAX_UPLOAD_BYTES))
  })

  it('管理员调小上限后，拒绝文案报的是设置里的数而不是兜底常量', () => {
    const r = validateUploadFiles([fakeFile('a.png', 6 * MB)], { maxBytes: 5 * MB })
    expect(r.rejected[0]?.reason).toContain(formatBytes(5 * MB))
    expect(r.rejected[0]?.reason).not.toContain(formatBytes(MAX_UPLOAD_BYTES))
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

describe('resolveAllowedExtensions（与服务端 _effective_library_exts 同口径）', () => {
  it('两项都留空＝不收紧，沿用内置安全清单', () => {
    expect(resolveAllowedExtensions('', '')).toEqual(ALLOWED_UPLOAD_EXTENSIONS)
    expect(resolveAllowedExtensions(undefined, null)).toEqual(ALLOWED_UPLOAD_EXTENSIONS)
  })

  it('配置只能收紧：去掉 svg 后 .svg 不再放行，其余仍在', () => {
    const r = resolveAllowedExtensions('jpg,png,webp,gif', undefined)
    expect(r).toEqual(['jpg', 'png', 'gif', 'webp'])
    expect(r).not.toContain('svg')
  })

  it('配置放松无效：清单里写 zip/exe 也不会出现在结果里（内置清单是安全边界）', () => {
    const r = resolveAllowedExtensions('jpg', 'pdf,zip,exe,php')
    expect(r).toEqual(['jpg', 'pdf'])
    for (const bad of ['zip', 'exe', 'php']) expect(r).not.toContain(bad)
  })

  it('容忍点号、大小写与空白（后台文案里输入 .PNG 是常态）', () => {
    // 结果顺序始终按内置清单，与输入顺序无关
    expect(resolveAllowedExtensions(' .PNG , jpeg ', undefined)).toEqual(['jpeg', 'png'])
  })

  it('交集为空就是空——后端此时也一律 400，前端不能假装能传', () => {
    expect(resolveAllowedExtensions('zip,rar', '')).toEqual([])
    const r = validateUploadFiles([fakeFile('a.png', 1024)], { allowedExtensions: [] })
    expect(r.rejected[0]?.reason).toContain('不支持的文件类型')
  })
})

describe('消费点接线', () => {
  const library = readFileSync(resolve(process.cwd(), 'pages/admin/media/library.vue'), 'utf8')
  const zone = readFileSync(resolve(process.cwd(), 'components/ImageUploadZone.vue'), 'utf8')

  it('媒体库把 /api/config 的上限与白名单一起传给预检，accept 也从同一份清单派生', () => {
    expect(library).toMatch(/resolveUploadLimitBytes\(siteState\.value\.publicConfig\?\.max_upload_size\)/)
    expect(library).toMatch(/resolveAllowedExtensions\(\s*siteState\.value\.publicConfig\?\.allowed_image_types,\s*siteState\.value\.publicConfig\?\.allowed_file_types\s*\)/)
    expect(library).toMatch(/maxBytes: uploadMaxBytes\.value,\s*\n\s*allowedExtensions: uploadExtensions\.value/)
    expect(library).toMatch(/:accept="uploadAccept"/)
    expect(library).toMatch(/const uploadAccept = computed\(\(\) => uploadExtensions\.value\.map/)
    // 硬编码副本只能作为兜底清单存在，不能再直接喂给 accept
    expect(library).not.toMatch(/ALLOWED_UPLOAD_EXTENSIONS\.map/)
  })

  it('图片上传区的提示与判定共用同一份上限，且不再有写死的 maxSize prop', () => {
    expect(zone).toMatch(/resolveUploadLimitBytes\(siteState\.value\.publicConfig\?\.max_upload_size\)/)
    // 提示语已 i18n 化：文案走 image.formatHint，占位符仍喂同一份 limitLabel
    expect(zone).toMatch(/t\('image\.formatHint',\s*\{\s*max:\s*limitLabel\s*\}\)/)
    expect(zone).toMatch(/const limitLabel = computed\(\(\) => formatBytes\(limitBytes\.value\)\)/)
    expect(zone).toMatch(/f\.size > limitBytes\.value/)
    expect(zone).not.toMatch(/props\.maxSize/)
    expect(zone).not.toMatch(/maxSize\?:\s*number/)
  })

  it('图片上传区的扩展名判定也走同一份配置清单', () => {
    expect(zone).toMatch(/resolveAllowedExtensions\(\s*siteState\.value\.publicConfig\?\.allowed_image_types,\s*siteState\.value\.publicConfig\?\.allowed_file_types\s*\)/)
    expect(zone).toMatch(/allowedExtensions\.value\.includes\(ext\)/)
  })
})

/**
 * 后台「单文件大小上限」输入框的 min/max 是管理员看到的唯一契约，而服务端
 * api/media.py::_effective_upload_limit 会把值钳进自己的区间、接口照样回 200。
 * 两边不同数时的表现：写 500MB 保存成功、回显 500MB，实际生效 100MB——
 * 又是一次"这个设置没生效"（与写死 20MB 预检同族）。
 */
describe('设置页输入区间 ↔ 服务端钳位区间', () => {
  const media = readFileSync(resolve(process.cwd(), '../backend/api/media.py'), 'utf8')
  const page = readFileSync(resolve(process.cwd(), 'pages/admin/system/settings.vue'), 'utf8')

  it('服务端区间不变（改这里必须同步设置页）', () => {
    expect(media).toMatch(/UPLOAD_SIZE_CEILING_BYTES = 100 \* 1024 \* 1024/)
    expect(media).toMatch(/UPLOAD_SIZE_FLOOR_BYTES = 64 \* 1024/)
  })

  it('设置页 min/max 就是那两个边界，且 help 把区间写在脸上', () => {
    expect(page).toMatch(/max_upload_size: \{\s*min: 65536,\s*max: 104857600,/)
    expect(page).toMatch(/65536 - 104857600/)
  })
})
