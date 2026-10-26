/**
 * purge-cache 端点读请求头：三种 event 形态都要能拿到密钥。
 *
 * 背景：Nitro 2.13 的路由处理器拿到 web 形态 event，h3 的 `getRequestHeader`
 * 走 `event.node.req.headers`（在该路由里是空对象），实测恒返回 undefined。
 * 后果不是"读不到日志"这么轻——后端带密钥来清缓存时会被 403 拒绝，
 * 主题切换 / 独立页改动在整个 SWR 窗口内都不生效，而且后端是 fire-and-forget，
 * 失败只记 debug。这里把三种形态逐个钉住。
 */

import { describe, it, expect } from 'vitest'

import { PURGE_SECRET_HEADER, readPurgeSecretHeader } from '../../server/utils/purgeSecret'

const SECRET = 'probe-secret'

function webHeaders(): Headers {
  return new Headers({ [PURGE_SECRET_HEADER]: SECRET })
}

describe('readPurgeSecretHeader', () => {
  it('web 形态：request.headers（Headers 实例）', () => {
    expect(readPurgeSecretHeader({ req: { headers: webHeaders() } })).toBe(SECRET)
  })

  it('web 形态：event.headers 也可读（部分适配器直接挂在这里）', () => {
    expect(readPurgeSecretHeader({ headers: webHeaders() })).toBe(SECRET)
  })

  it('node 形态：event.node.req.headers（h3 原始对象）', () => {
    expect(
      readPurgeSecretHeader({ node: { req: { headers: { [PURGE_SECRET_HEADER]: SECRET } } } })
    ).toBe(SECRET)
  })

  it('node 形态：重复头由 h3 合并成一个字符串（数组分支只是防御）', () => {
    // Node 的 http 层对多数头已经做过 join，h3 读到的是字符串；
    // 这里断言"能拿到值"，不去猜具体的合并格式。
    expect(
      readPurgeSecretHeader({
        node: { req: { headers: { [PURGE_SECRET_HEADER]: [SECRET, 'other'] } } }
      })
    ).toContain(SECRET)
  })

  it('任何形态都拿不到时返回空串（调用方按 403 处理，fail closed）', () => {
    expect(readPurgeSecretHeader({})).toBe('')
    expect(readPurgeSecretHeader({ req: { headers: new Headers() } })).toBe('')
    expect(readPurgeSecretHeader(null)).toBe('')
  })

  // 实测：本地 node-server 产物里请求对象的 `headers` 是空对象，
  // 而 `rawHeaders` 完整（Host / User-Agent / 自定义头都在）。
  // 少了这条兜底，purge 端点在生产构建里恒 403。
  it('node 形态：headers 为空时从 rawHeaders 兜底', () => {
    expect(
      readPurgeSecretHeader({
        node: {
          req: {
            headers: {},
            rawHeaders: ['Host', '127.0.0.1:3010', 'X-Rosetta-Purge-Secret', SECRET]
          }
        }
      })
    ).toBe(SECRET)
  })

  it('rawHeaders 里没有该头时仍返回空串', () => {
    expect(
      readPurgeSecretHeader({
        node: { req: { headers: {}, rawHeaders: ['Host', 'example.com'] } }
      })
    ).toBe('')
  })

  it('与后端约定的头名保持一致', () => {
    expect(PURGE_SECRET_HEADER).toBe('x-rosetta-purge-secret')
  })
})
