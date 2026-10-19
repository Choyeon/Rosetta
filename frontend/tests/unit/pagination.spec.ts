/**
 * 分页页码窗口单源守卫：`pageWindow` 是 6 个公开列表页共用的页码条算法。
 *
 * 断言按旧实现逐字对拍（窗口宽度 5：先按当前页居中开窗，尾部不足就把窗口整体往前挪），
 * 目的是让"抽函数"这一步**零行为变化**；改这些期望值就等于同时改了 6 个页面的页码条。
 */
import { describe, it, expect } from 'vitest'
import { PAGE_WINDOW_SIZE, pageWindow } from '@/lib/pagination'

describe('pageWindow', () => {
  it('默认窗口宽度 5（改了会让页码条整排变宽/变窄）', () => {
    expect(PAGE_WINDOW_SIZE).toBe(5)
    expect(pageWindow(1, 100)).toHaveLength(5)
  })

  it('首页：窗口贴左，不会显示 0 或负数页码', () => {
    expect(pageWindow(1, 10)).toEqual([1, 2, 3, 4, 5])
    expect(pageWindow(2, 10)).toEqual([1, 2, 3, 4, 5])
  })

  it('中间页：当前页居中', () => {
    expect(pageWindow(5, 10)).toEqual([3, 4, 5, 6, 7])
  })

  it('尾页：窗口整体往前挪，凑满 5 个而不是少显示一半', () => {
    expect(pageWindow(9, 10)).toEqual([6, 7, 8, 9, 10])
    expect(pageWindow(10, 10)).toEqual([6, 7, 8, 9, 10])
  })

  it('总页数不足窗口时只回真实页数', () => {
    expect(pageWindow(1, 2)).toEqual([1, 2])
    expect(pageWindow(1, 1)).toEqual([1])
  })

  it('当前页越界（分享出去的 ?page=9 而库里只剩 3 页）时拉回最后一个满窗口，页码条不整条消失', () => {
    expect(pageWindow(9, 3)).toEqual([1, 2, 3])
  })

  it('没有内容时回空数组，而不是凭空点亮一个"第 1 页"', () => {
    expect(pageWindow(1, 0)).toEqual([])
  })

  it('自定义窗口宽度同样成立', () => {
    expect(pageWindow(3, 10, 3)).toEqual([2, 3, 4])
    expect(pageWindow(10, 10, 3)).toEqual([8, 9, 10])
  })
})
