/**
 * 相册网格缩略图 / 灯箱原图的分档契约（批次 #232）。
 *
 * 后端 `Media.sizes` 在上传时就生成 thumbnail/medium/large 三档，但相册照片读取口从不派生，
 * `PhotoResponse.thumbnail_url` 恒为 null，于是**前台相册网格和后台网格全部下载原图**：
 * 一屏 8 张手机直出的 JPEG 就是十几 MB，移动网络下相册页等于自缚带宽。
 *
 * 接上投影后有一条新坑必须同时钉住：viewerjs 的 `DEFAULTS.url` 是 `'src'`
 * （`getImageURL() === image.getAttribute(this.options.url)`），所以模板里那个
 * `data-original` 一直是**装饰属性**、从没被读过。把网格 `src` 换成缩略图时如果忘了给
 * Viewer 传 `url: 'data-original'`，表现是「点开相册，灯箱里放大的是那张 150px 糊图」——
 * 比原来的「慢但清晰」更糟。两条必须一起改，所以一起钉。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const publicPage = readFileSync(resolve(ROOT, 'pages/gallery.vue'), 'utf8')
const adminPage = readFileSync(resolve(ROOT, 'pages/admin/media/gallery.vue'), 'utf8')

const gridBlock = (() => {
  const start = publicPage.indexOf('v-for="(photo, idx) in currentPhotos"')
  return publicPage.slice(start, start + 700)
})()

const viewerOptions = publicPage.slice(
  publicPage.indexOf('viewerInstance = new Ctor(el'),
  publicPage.indexOf('viewerInstance = new Ctor(el') + 900
)

describe('公开相册页：照片携带原图与缩略档两个地址', () => {
  it('photos 不再是裸字符串数组，而是 { url, thumb }', () => {
    expect(publicPage).toMatch(/photos: AlbumPhoto\[\]/)
    expect(publicPage).toMatch(/interface AlbumPhoto \{[\s\S]*?url: string[\s\S]*?thumb: string/)
    expect(publicPage).not.toMatch(/photos: string\[\]/)
  })

  it('详情响应的单张照片有显式形状（thumb 可缺省）', () => {
    expect(publicPage).toMatch(/interface AlbumDetail \{/)
    expect(publicPage).toMatch(/thumbnail_url\?: string \| null/)
  })

  it('解包时同时读 url / thumbnail_url，且没有 url 的行仍然被丢掉', () => {
    expect(publicPage).toMatch(/\bphotosArr\b/)
    expect(publicPage).toMatch(/obj\.url/)
    expect(publicPage).toMatch(/obj\.thumbnail_url/)
    expect(publicPage).toMatch(/if \(!url\) return null/)
  })
})

describe('公开相册页：网格下缩略图、灯箱用原图', () => {
  it('网格 src 是 thumb 回落 url，data-original 钉死在原图', () => {
    expect(gridBlock).toMatch(/:src="photo\.thumb \|\| photo\.url"/)
    expect(gridBlock).toMatch(/:data-original="photo\.url"/)
    expect(gridBlock).toMatch(/:key="photo\.url"/)
  })

  it('不再出现「src 与 data-original 同一个裸变量」的旧写法', () => {
    expect(gridBlock).not.toMatch(/:src="photo"\s/)
    expect(gridBlock).not.toMatch(/:data-original="photo"\s/)
  })

  it('Viewer 显式声明 url: "data-original"（否则默认读 src，灯箱就是那张缩略图）', () => {
    expect(viewerOptions).toMatch(/url: 'data-original'/)
    // 选项必须在构造参数对象里，写在注释里不算
    expect(viewerOptions.indexOf('url:')).toBeLessThan(viewerOptions.indexOf('toolbar:'))
  })

  it('页首契约注释同步说明两档地址与灯箱口径', () => {
    const header = publicPage.slice(0, publicPage.indexOf('<template>'))
    expect(header).toMatch(/缩略/)
    expect(header).toMatch(/data-original/)
    expect(header).not.toMatch(/photos 只取字符串 url 项/)
  })
})

describe('后台相册页：只有网格吃缩略图', () => {
  it('文件名取原图地址（缩略档带 -thumbnail 后缀，会误导运营）', () => {
    const body = adminPage.slice(
      adminPage.indexOf('function photoFilename'),
      adminPage.indexOf('function photoFilename') + 260
    )
    expect(body).toMatch(/photoFullSrc\(p\)/)
    expect(body).not.toMatch(/const src = photoSrc\(p\)/)
  })

  it('封面、灯箱、编辑预览仍走原图', () => {
    expect(adminPage).toMatch(/:src="photoFullSrc\(editingPhoto\)"/)
    expect(adminPage).toMatch(/url: photoFullSrc\(p\)/)
    expect(adminPage).toMatch(/const url = photoFullSrc\(p\)/)
  })

  it('网格吃 thumbnail_url 并回落原图', () => {
    expect(adminPage).toMatch(/p\.thumbnail_url \|\| photoFullSrc\(p\)/)
    expect(adminPage).toMatch(/:src="photoSrc\(p\)"/)
  })

  it('页首契约不再把 thumbnail_url 写成"不落库的透传字段"', () => {
    const header = adminPage.slice(0, adminPage.indexOf('<template>'))
    expect(header).not.toMatch(/thumbnail_url 是不落库的透传字段/)
    expect(header).toMatch(/sizes/)
  })
})
