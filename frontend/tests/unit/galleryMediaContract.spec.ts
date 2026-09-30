/**
 * 相册（Gallery）与媒体（Media）的跨端契约守卫（扫源码文本，不挂组件）。
 *
 * 这一组不变量的共同点：全都是「写法」层面的错，类型检查和运行时都不会报错，
 * 但线上会立刻出问题——
 *
 * ① AdminAlbum 的 title/description 必须收窄成 string：写成 i18n dict 联合类型
 *    会逼出永远走不到的分支，还会让人误以为相册标题支持多语言；
 * ② 相册写路径必须清前台页面缓存——/gallery 是 SSR 页且 swr 600，漏一次就是
 *    「管理员改完十分钟才生效」；
 * ③ 写路径发的钩子事件必须在 WEBHOOK_EVENTS 登记，否则后台订阅 UI 里根本选不到；
 * ④ 媒体资源库的「文件类型」筛选必须覆盖后端全部四类（历史上漏了 audio）；
 * ⑤ 公开画廊页的详情请求失败不能再静默吞掉（点了相册什么都不出现）。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), 'utf8')

/**
 * 取某个 handler 所在的「路由块」。
 *
 * 这些模块的结构是「一个装饰器 + 一个 handler」，按装饰器切块最准。
 * 不能用 `\Z` 之类的「到文件末尾」写法：JS 正则没有 `\Z`（会被当成字面量 Z），
 * 而用 `$` + `m` 又会让非贪婪匹配在行尾就收住，两种写法都会静默给出空串。
 */
function routeBlock(source: string, name: string): string {
  const blocks = source.split(/^(?=@(?:admin|public)?_?router\.)/m)
  return blocks.find(b => b.includes(`async def ${name}(`)) ?? ''
}

const manage = read('composables/useAdminManage.ts')
const galleryPage = read('pages/admin/media/gallery.vue')
const libraryPage = read('pages/admin/media/library.vue')
const publicGallery = read('pages/gallery.vue')
const galleryApi = read('../backend/api/gallery.py')
const mediaApi = read('../backend/api/media.py')
const webhookApi = read('../backend/api/webhook.py')

describe('AdminAlbum 类型与后端 Gallery 契约一致', () => {
  const block = manage.match(/export interface AdminAlbum \{[\s\S]*?\n\}/)?.[0] ?? ''

  it('title 是 string，不是 i18n dict 联合类型', () => {
    expect(block).toMatch(/^\s*title: string$/m)
    expect(block).not.toMatch(/Record<string, string>/)
  })

  it('description 是 string | null，同样不含 dict 分支', () => {
    expect(block).toMatch(/^\s*description: string \| null$/m)
  })

  it('带 sort_order 与 updated_at（后端 AlbumResponse 有这两个字段）', () => {
    expect(block).toMatch(/^\s*sort_order: number$/m)
    expect(block).toMatch(/^\s*updated_at: string \| null$/m)
  })

  it('mapAlbum 不再把 payload 的 dict 形态透传出去', () => {
    const mapper = manage.match(/function mapAlbum[\s\S]*?\n\}/)?.[0] ?? ''
    expect(mapper).toMatch(/typeof r\.title === 'string'/)
    expect(mapper).not.toMatch(/as AdminAlbum\[/)
  })

  it('albumBody 不再保留 dict→zh 的降级分支（字段本来就不是 dict）', () => {
    const body = manage.match(/function albumBody[\s\S]*?\n\}/)?.[0] ?? ''
    expect(body).not.toMatch(/t\.zh|d\.zh/)
  })
})

describe('后台相册页不保留死分支、补齐 sort_order 与清除封面', () => {
  it('不再有 dict 形态的 displayField', () => {
    expect(galleryPage).not.toMatch(/function displayField/)
    expect(galleryPage).not.toMatch(/obj\.zh as string/)
  })

  it('表单可编辑 sort_order', () => {
    expect(galleryPage).toMatch(/id="album-sort-input"/)
    expect(galleryPage).toMatch(/sort_order: Number\.isFinite\(/)
  })

  it('可以清除封面（把表单里的封面置空）', () => {
    expect(galleryPage).toMatch(/function clearCover/)
  })

  it('提交时 cover 为空串要给后端 null（后端 cover 是 str | None）', () => {
    expect(galleryPage).toMatch(/cover: albumForm\.cover_url \|\| null/)
  })
})

describe('相册写路径的横切约束（后端）', () => {
  it('每个写路径都调了 _purge_frontend', () => {
    const writeHandlers = [
      'admin_create_album',
      'admin_update_album',
      'admin_delete_album',
      'admin_create_photo',
      'admin_update_photo',
      'admin_delete_photos_batch',
      'admin_delete_photo'
    ]
    for (const name of writeHandlers) {
      const body = routeBlock(galleryApi, name)
      expect(body, `未找到 ${name} 的函数体`).toBeTruthy()
      expect(body, `${name} 未清前台页面缓存`).toMatch(/_purge_frontend\(/)
    }
  })

  it('_purge_frontend 走的是 frontend_cache_purge 服务', () => {
    expect(galleryApi).toMatch(/from backend\.services\.frontend_cache_purge import purge_frontend_page_cache/)
    expect(galleryApi).toMatch(/def _purge_frontend\([\s\S]*?purge_frontend_page_cache\(/)
  })

  it('写路径 do_action 的事件名与批量路径保持一致', () => {
    expect(galleryApi).toMatch(/bus\.do_action\(\s*"album\.created"/)
    expect(galleryApi).toMatch(/bus\.do_action\(\s*"album\.updated"/)
    expect(galleryApi).toMatch(/bus\.do_action\(\s*"album\.deleted"/)
    expect(galleryApi).toMatch(/bus\.do_action\(\s*"photo\.created"/)
    expect(galleryApi).toMatch(/bus\.do_action\(\s*"photo\.updated"/)
    // 批量与单条同构：事件名必须同样是 photo.deleted
    expect(galleryApi).toMatch(/bus\.do_action\(\s*"photo\.deleted"/)
  })

  it('批量删除为每张实际删除的照片发一条，而不是整批发一次', () => {
    const batch = routeBlock(galleryApi, 'admin_delete_photos_batch')
    expect(batch).toMatch(/for photo_id, album_id in sorted\(rows\)/)
    expect(batch).toMatch(/_purge_frontend\(f"批量删除照片/)
  })

  it('跨相册移动先校验目标相册存在', () => {
    const update = routeBlock(galleryApi, 'admin_update_photo')
    expect(update).toMatch(/target = await db\.get\(Album, data\.album_id\)/)
    expect(update).toMatch(/detail="相册不存在"/)
  })

  it('钩子事件已在 WEBHOOK_EVENTS 登记', () => {
    for (const event of ['album.created', 'album.updated', 'album.deleted',
      'photo.created', 'photo.updated', 'photo.deleted',
      'media.updated', 'media.deleted']) {
      expect(webhookApi, `${event} 未登记`).toMatch(new RegExp(`"${event.replace('.', '\\.')}"`))
    }
  })
})

describe('媒体后端的约束', () => {
  it('MEDIA_DIR 由 settings.media_dir 派生，不再硬编码 "media"', () => {
    expect(mediaApi).toMatch(/MEDIA_DIR = Path\(settings\.media_dir\)/)
    expect(mediaApi).not.toMatch(/MEDIA_DIR = Path\("media"\)/)
  })

  it('删除钩子的载荷在 db.delete 之前建立', () => {
    expect(mediaApi).toMatch(/def _media_payload\(media: Media\)/)
    const single = routeBlock(mediaApi, 'delete_media_by_id')
    // 载荷必须早于 db.delete：ORM 实例进了 deleted 态后字段不一定还能读
    const payloadAt = single.indexOf('payload = _media_payload(media)')
    const deleteAt = single.indexOf('await db.delete(media)')
    expect(payloadAt).toBeGreaterThan(-1)
    expect(deleteAt).toBeGreaterThan(payloadAt)
  })
})

describe('后台媒体资源库：筛选覆盖后端全部四类', () => {
  const backendTypes = mediaApi.match(/LIBRARY_TYPE_EXTENSIONS[\s\S]*?\n\}/)?.[0] ?? ''
  const declared = [...backendTypes.matchAll(/^\s{4}"(\w+)":/gm)].map(m => m[1])

  it('后确实声明了 image / video / audio / document', () => {
    expect(declared.sort()).toEqual(['audio', 'document', 'image', 'video'])
  })

  it('前端下拉四类齐全（历史上漏过 audio）', () => {
    for (const type of declared) {
      expect(libraryPage, `筛选下拉缺少 ${type}`).toMatch(new RegExp(`<SelectItem value="${type}">`))
    }
  })

  it('筛选函数按白名单取值，不把任意字符串透传给后端', () => {
    expect(libraryPage).toMatch(/function fileTypeFilter\(\)/)
    expect(libraryPage).toMatch(/allowed\.has\(mimeFilter\.value\)/)
  })
})

describe('公开画廊页：详情加载失败必须可见', () => {
  it('loadAlbumDetail 不再用空 catch 吞掉异常', () => {
    const loader = publicGallery.match(/async function loadAlbumDetail\([\s\S]*?\n\}/)?.[0] ?? ''
    expect(loader).toBeTruthy()
    expect(loader).not.toMatch(/catch \{/)
    expect(loader).toMatch(/catch \(err\)/)
    expect(loader).toMatch(/detailError\.value = true/)
  })

  it('提供重试入口，并先清掉 loaded 守卫', () => {
    expect(publicGallery).toMatch(/function retryDetail\(\)/)
    expect(publicGallery).toMatch(/album\.loaded = false/)
  })

  it('错误态与「相册本来就没有照片」区分开', () => {
    expect(publicGallery).toMatch(/v-if="detailError"/)
  })
})
