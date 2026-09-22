import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, type Component } from 'vue'
import DynamicIcon from '~/components/DynamicIcon.vue'
import { HomeIcon, Squares2X2Icon } from '@heroicons/vue/24/outline'

/** Render a component on its own so we can compare its real SVG output. */
function renderSvg(comp: Component): string {
  const Host = defineComponent({ setup: () => () => h(comp) })
  return mount(Host).html()
}

/** The concatenated `d` attributes — a fingerprint of WHICH icon was drawn. */
function pathFingerprint(html: string): string {
  return (html.match(/\sd="[^"]*"/g) ?? []).join('|')
}

function fingerprintOf(icon: string, extraClass?: string): string {
  const wrapper = mount(DynamicIcon, {
    props: { icon, ...(extraClass ? { class: extraClass } : {}) }
  })
  return pathFingerprint(wrapper.html())
}

describe('DynamicIcon', () => {
  it('renders the REAL heroicons component for a heroicons name', () => {
    const wrapper = mount(DynamicIcon, { props: { icon: 'heroicons:home' } })

    expect(wrapper.find('svg').exists()).toBe(true)
    // same path data as the genuine `HomeIcon` from @heroicons/vue
    expect(pathFingerprint(wrapper.html())).toBe(pathFingerprint(renderSvg(HomeIcon)))
    // and definitely not raw text
    expect(wrapper.text()).toBe('')
  })

  it('renders the same icon for a bare heroicons name', () => {
    expect(fingerprintOf('home')).toBe(pathFingerprint(renderSvg(HomeIcon)))
  })

  it('renders the same icon for the raw PascalCase export name', () => {
    expect(fingerprintOf('HomeIcon')).toBe(pathFingerprint(renderSvg(HomeIcon)))
  })

  it('renders the placeholder glyph when the name is unknown', () => {
    const wrapper = mount(DynamicIcon, {
      props: { icon: 'heroicons:totally-invalid' }
    })
    expect(pathFingerprint(wrapper.html())).toBe(pathFingerprint(renderSvg(Squares2X2Icon)))
  })

  it('applies the size class', () => {
    const wrapper = mount(DynamicIcon, {
      props: { icon: 'heroicons:tag', class: 'size-6' }
    })
    expect(wrapper.find('svg').classes()).toContain('size-6')
  })

  it('renders emoji as text', () => {
    const wrapper = mount(DynamicIcon, { props: { icon: '🎉' } })
    expect(wrapper.text()).toContain('🎉')
  })

  it('never leaks a namespaced icon string into the UI', () => {
    for (const icon of [
      'heroicons:totally-bogus-name',
      'material-symbols:totally-bogus-name',
      'whatever:totally-bogus-name'
    ]) {
      const wrapper = mount(DynamicIcon, { props: { icon } })
      expect(wrapper.text()).toBe('')
      expect(wrapper.find('svg').exists()).toBe(true)
    }
  })

  it('renders plain multi-word text as text', () => {
    const wrapper = mount(DynamicIcon, { props: { icon: 'Hello World' } })
    expect(wrapper.text()).toBe('Hello World')
  })
})
