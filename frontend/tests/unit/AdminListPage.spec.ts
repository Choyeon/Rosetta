import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AdminListPage from '~/components/admin/AdminListPage.vue'

/**
 * 回归锁定：AdminListPage 的页头内容必须真正渲染出来。
 *
 * 历史缺陷：计数徽标与 `<slot name="actions" />` 作为裸子节点传给 AdminPageHeader，
 * 而后者只有 #meta / #actions 两个具名出口、没有 default 插槽，于是「共 N 项」徽标
 * 和 5 个内容列表页（文章/分类/标签/系列/独立页）的「新建」按钮整体不渲染——
 * 页面看起来少了主操作入口，但没有任何报错。
 */

const BadgeStub = {
  name: 'Badge',
  props: ['variant'],
  template: '<span class="badge-stub"><slot /></span>'
}

const CardStub = {
  name: 'AdminCard',
  template: '<div class="card-stub"><slot /></div>'
}

function mountListPage(slots: Record<string, string> = {}) {
  return mount(AdminListPage, {
    props: { title: '分类管理', description: '描述', count: 12 },
    global: {
      stubs: { Badge: BadgeStub, AdminCard: CardStub }
      // AdminPageHeader 保持真实：被测的正是父子插槽接线
    },
    slots: {
      actions: '<button class="new-btn">+ 新建分类</button>',
      toolbar: '<div class="toolbar">搜索框</div>',
      pagination: '<nav class="pager">分页</nav>',
      default: '<table class="rows"><tbody /></table>',
      ...slots
    }
  })
}

describe('AdminListPage 插槽接线', () => {
  it('计数徽标渲染在页头标题旁（#meta）', () => {
    const wrapper = mountListPage()
    const badge = wrapper.find('.badge-stub')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('共 12 项')
    // 结构契约：徽标与 h1 同处一行容器内，而不是掉在页面别处
    expect(badge.element.parentElement?.textContent).toContain('分类管理')
  })

  it('count 省略时不渲染空徽标', () => {
    const wrapper = mount(AdminListPage, {
      props: { title: '无计数' },
      global: { stubs: { Badge: BadgeStub, AdminCard: CardStub } }
    })
    expect(wrapper.find('.badge-stub').exists()).toBe(false)
  })

  it('消费方 #actions 渲染进页头操作区', () => {
    const wrapper = mountListPage()
    const btn = wrapper.find('.new-btn')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('新建分类')
    // 操作区在页头内、工具栏之前：DOM 顺序即层级顺序
    const html = wrapper.html()
    expect(html.indexOf('<h1')).toBeLessThan(html.indexOf('new-btn'))
    expect(html.indexOf('new-btn')).toBeLessThan(html.indexOf('toolbar'))
  })

  it('toolbar / 默认内容 / pagination 各自落在自己的位置', () => {
    const wrapper = mountListPage()
    expect(wrapper.find('.toolbar').exists()).toBe(true)
    expect(wrapper.find('.card-stub .rows').exists()).toBe(true)
    expect(wrapper.find('.pager').exists()).toBe(true)
    // 顺序契约：页头 < 工具栏 < 内容卡 < 分页
    const html = wrapper.html()
    expect(html.indexOf('badge-stub')).toBeLessThan(html.indexOf('toolbar'))
    expect(html.indexOf('toolbar')).toBeLessThan(html.indexOf('rows'))
    expect(html.indexOf('rows')).toBeLessThan(html.indexOf('pager'))
  })
})
