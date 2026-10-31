/**
 * 批次 #135：灯箱里的「第几张」进地址栏（?album=3&photo=7）。
 *
 * 批次 #128 把「开着哪个相册」收成了 ?album=，但灯箱本身仍然是 viewerjs 的内部状态：
 * 分享链接只能分享整个相册，后退键从灯箱直接跳出相册页，刷新回到网格第一张。
 * 这里按源码断言钉住六段：
 * ① 序号从 1 起（网格没有第 0 张，`?photo=0` 一律按「没指定」处理）；
 * ② `?photo=` 只在「开着相册」时才写进查询串——关相册留一个没人读的照片号，
 *    下一次点开的却是另一个相册；
 * ③ 越界只清参数不 clamp（静默换成另一张照片等于让分享者和访问者看到不同内容）；
 * ④ viewed / hidden 双向同步，且同值不写 router.replace（翻一张灌一条重复 history）；
 * ⑤ watch(route.query.photo) 与 viewed 事件之间靠 viewerPhotoIndex 挡自反回路；
 * ⑥ 销毁只有一份（重入 / 关对话框 / 卸载），并顺带清掉对照下标，
 *    否则下一次 watch 会误判「灯箱已经在这张」而什么都不做。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/gallery.vue'), 'utf-8').replace(/\r\n/g, '\n')

describe('相册页 ?photo= 灯箱深链', () => {
  it('序号 1 基解析：非整数与 <=0 一律当「没指定」', () => {
    expect(src).toContain('const photoIndexFromQuery = (raw: unknown): number | null')
    expect(src).toContain('Number.isInteger(n) && n > 0 ? n - 1 : null')
  })

  it('?photo= 只在开着相册时写进查询串（关相册 / 换相册都带走）', () => {
    expect(src).toMatch(/const albumQuery = \(page: number \| null, albumId: number \| null = activeAlbumId\.value, photo: number \| null = null\)/)
    expect(src).toMatch(/if \(albumId !== null\) \{\s*query\.album = String\(albumId\)/)
    expect(src).toContain('if (photo !== null && photo >= 0) query.photo = String(photo + 1)')
  })

  it('灯箱事件双向同步：翻一张写地址栏，收起时清参数', () => {
    expect(src).toMatch(/viewed: \(event\) => \{\s*viewerPhotoIndex = photoIndexFromViewerEvent\(event\)\s*syncPhotoQuery\(viewerPhotoIndex\)/)
    expect(src).toMatch(/hidden: \(\) => \{\s*viewerPhotoIndex = null\s*syncPhotoQuery\(null\)/)
    expect(src).toMatch(/const n = detail\?\.index/)
    expect(src).toMatch(/return typeof n === 'number' && Number\.isInteger\(n\) && n >= 0 \? n : null/)
  })

  it('同值不重写地址栏，且只在客户端写（SSR 期 replace 会把一次渲染变成第二次导航）', () => {
    expect(src).toMatch(/const want = index === null \|\| index < 0 \? '' : String\(index \+ 1\)/)
    expect(src).toMatch(/const got = typeof route\.query\.photo === 'string' \? route\.query\.photo : ''/)
    expect(src).toMatch(/if \(want === got\) return/)
    expect(src).toMatch(/function syncPhotoQuery\(index: number \| null\) \{\s*if \(!import\.meta\.client\) return/)
  })

  it('深链开灯箱走 view(序号)，越界只清参数不 clamp', () => {
    expect(src).toMatch(/await initViewer\(\)\s*openSharedPhoto\(\)/)
    expect(src).toMatch(/if \(!viewerInstance \|\| idx >= currentPhotos\.value\.length\) \{\s*syncPhotoQuery\(null\)/)
    expect(src).toMatch(/viewerPhotoIndex = idx\s*viewerInstance\.view\(idx\)/)
    // 反向：不得有 Math.min 之类的静默钳位
    expect(src).not.toMatch(/viewerInstance\.view\(Math\.min/)
  })

  it('后退 / 前进改 ?photo= 由 watch 接手，值相同直接返回（挡住 viewed → 写 URL → watch 回路）', () => {
    expect(src).toMatch(/watch\(\(\) => route\.query\.photo, \(raw\) => \{/)
    expect(src).toMatch(/if \(idx === viewerPhotoIndex\) return/)
    // 灯箱没实例化时不动 URL：留着参数由相册流程读到，这里清掉等于吃掉一条分享链接
    expect(src).toMatch(/if \(!viewerInstance\) \{[\s\S]{0,200}?return\s*\}/)
    expect(src).toMatch(/viewerPhotoIndex = null\s*viewerInstance\.hide\(\)/)
  })

  it('销毁只有一份，且对照下标跟着清', () => {
    expect(src).toMatch(/function destroyViewer\(\) \{/)
    expect(src).toMatch(/viewerInstance = null\s*\}\s*viewerPhotoIndex = null\s*\}/)
    expect((src.match(/viewerInstance\.destroy\(\)/g) ?? []).length).toBe(1)
    expect((src.match(/destroyViewer\(\)/g) ?? []).length).toBe(4)
  })

  it('实例类型带得上 view / hide（原来只声明 destroy，深链开灯箱就是 TS 报错）', () => {
    expect(src).toMatch(/let viewerInstance: \{ destroy: \(\) => void, view: \(index: number\) => void, hide: \(\) => void \} \| null = null/)
  })
})
