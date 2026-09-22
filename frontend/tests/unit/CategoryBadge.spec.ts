import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import CategoryBadge from '~/components/CategoryBadge.vue'
import { CodeBracketIcon } from '@heroicons/vue/24/outline'

function pathFingerprint(html: string): string {
  return (html.match(/\sd="[^"]*"/g) ?? []).join('|')
}

function realSvg(comp: typeof CodeBracketIcon): string {
  const Host = defineComponent({ setup: () => () => h(comp) })
  return mount(Host).html()
}

/** NuxtLink needs a real Nuxt app instance; render it as a plain <a> instead. */
const NuxtLinkStub = {
  name: 'NuxtLink',
  props: ['to'],
  template: '<a :href="to"><slot /></a>'
}

function mountBadge(props: InstanceType<typeof CategoryBadge>['$props']) {
  return mount(CategoryBadge, {
    props,
    global: { stubs: { NuxtLink: NuxtLinkStub } }
  })
}

describe('CategoryBadge', () => {
  it('renders a real link when `to` is provided', () => {
    const wrapper = mountBadge({ label: '技术', to: '/categories/tech' })
    expect(wrapper.find('a').exists()).toBe(true)
    expect(wrapper.find('a').attributes('href')).toBe('/categories/tech')
  })

  it('renders a plain span (not a link) without `to`', () => {
    const wrapper = mount(CategoryBadge, { props: { label: '技术' } })
    expect(wrapper.find('a').exists()).toBe(false)
    expect(wrapper.find('span.cat-chip').exists()).toBe(true)
  })

  it('renders the label text', () => {
    const wrapper = mount(CategoryBadge, { props: { label: '随笔' } })
    expect(wrapper.text()).toContain('随笔')
  })

  it('derives HSL custom properties from the category colour', () => {
    const wrapper = mount(CategoryBadge, {
      props: { label: '技术', color: '#3b82f6' }
    })
    const style = wrapper.find('.cat-chip').attributes('style') ?? ''
    expect(style).toContain('--cat-h')
    expect(style).toContain('--cat-s')
    expect(style).toContain('--cat-l')
  })

  it('omits colour vars when no colour is given (falls back to theme)', () => {
    const wrapper = mount(CategoryBadge, { props: { label: '技术' } })
    const style = wrapper.find('.cat-chip').attributes('style') ?? ''
    expect(style).not.toContain('--cat-h')
  })

  it('renders the heroicon when an icon name is provided', () => {
    const wrapper = mount(CategoryBadge, {
      props: { label: '技术', icon: 'heroicons:code-bracket' }
    })
    // the real Heroicons `CodeBracketIcon`, not the inline folder fallback
    expect(pathFingerprint(wrapper.html())).toBe(pathFingerprint(realSvg(CodeBracketIcon)))
    expect(wrapper.find('svg').classes()).toContain('cat-icon')
  })

  it('falls back to the folder glyph when no icon is provided', () => {
    const wrapper = mount(CategoryBadge, { props: { label: '技术' } })
    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('svg').classes()).toContain('cat-icon')
  })

  it('renders the accent bar', () => {
    const wrapper = mount(CategoryBadge, { props: { label: '技术' } })
    expect(wrapper.find('.cat-accent').exists()).toBe(true)
  })

  it('applies the size class', () => {
    const wrapper = mount(CategoryBadge, { props: { label: '技术', size: 'sm' } })
    expect(wrapper.find('.cat-chip').classes()).toContain('cat-sm')
  })
})
