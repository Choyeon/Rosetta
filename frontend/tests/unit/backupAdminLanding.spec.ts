/**
 * 全站备份/恢复的前台落地契约。
 *
 * 起因：`/admin/backup/info|full|restore` 三条端点早已实现（含解压炸弹三道闸门、
 * 按外键顺序导入、缓存连带失效），但前台一个入口都没有——而本页"导入"Tab 的确认
 * 文案一直在建议管理员"先做一次全站备份"，即建议一件没有入口的事。
 * 这类缺口的表现不是报错，是"功能看起来不存在"，所以钉成门禁。
 *
 * 另一半价值在跨语言常量对齐：前端前置校验的 20MB 必须等于后端 MAX_BACKUP_BYTES，
 * 两边各自演进的结果是"前端放行的包在后端 413"，用户只会看到一个莫名失败。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const PAGE_REL = 'pages/admin/tools/import-export.vue'
const BACKEND_REL = '../backend/api/import_export.py'

const page = readFileSync(resolve(process.cwd(), PAGE_REL), 'utf8')
const backend = readFileSync(resolve(process.cwd(), BACKEND_REL), 'utf8')

describe('全站备份/恢复 · 后台落地契约', () => {
  it('三条备份端点都有真实调用', () => {
    for (const path of ['/admin/backup/info', '/admin/backup/full', '/admin/backup/restore']) {
      expect(page, `页面必须调用 ${path}`).toContain(`'${path}'`)
    }
    expect(page).toContain("apiFetch<Blob>('/admin/backup/full'")
    // 恢复是 multipart：文件走请求体，不能拼进 URL
    expect(page).toMatch(/fd\.append\('file', restoreForm\.file\)/)
  })

  it('恢复必须走危险确认弹窗，覆盖策略还要输入确认短语', () => {
    expect(page).toMatch(/<DangerConfirmDialog[\s\S]*v-model:open="restoreConfirmOpen"/)
    expect(page).toMatch(/:on-confirm="runRestore"/)
    expect(page).toMatch(/confirm-phrase="restoreForm\.strategy === 'overwrite' \? '全站覆盖' : '全站恢复'/)
  })

  it('前端体积上限与后端 MAX_BACKUP_BYTES 同值', () => {
    // 两边都写成 `20 * 1024 * 1024` 形态，直接算乘积比较，不用 eval
    const toBytes = (raw?: string) =>
      raw ? raw.split('*').map(part => Number(part.trim())).reduce((a, b) => a * b, 1) : NaN
    const backendBytes = toBytes(backend.match(/\bMAX_BACKUP_BYTES\s*=\s*([^#\n]+)/)?.[1])
    const frontendBytes = toBytes(page.match(/MAX_BACKUP_UPLOAD_BYTES\s*=\s*([^\n]+)/)?.[1])
    expect(backendBytes, '后端常量应可解析').toBeGreaterThan(0)
    expect(frontendBytes, '前端常量应可解析').toBe(backendBytes)
  })

  it('不得承诺备份包含磁盘媒体文件本体', () => {
    expect(page, '必须写清楚只备份数据库行').toMatch(/不含磁盘上的媒体文件本体/)
    expect(page).toMatch(/媒体文件本体不会被重建/)
  })

  it('恢复结果按 error_count 判失败，不写成"恢复完成"', () => {
    expect(page).toMatch(/failed > 0[\s\S]{0,80}toast\.warning/)
    expect(page).toMatch(/r\?\.success !== false/)
  })
})
