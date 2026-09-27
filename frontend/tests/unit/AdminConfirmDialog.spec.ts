import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import AdminConfirmDialog from '~/components/admin/AdminConfirmDialog.vue'

/**
 * 回归锁定：确认弹窗必须真正 await 执行回调。
 *
 * 历史缺陷是 `await emit('confirm')` —— emit() 恒返回 undefined，父组件的 async handler
 * 既 await 不到、也无法表达失败，于是「删除失败」和「删除成功」都会立刻关弹窗。
 * 现契约是 `onConfirm` prop：resolve 才关闭，reject 保持打开且期间不重复提交。
 */

// reka-ui 的 Dialog 在 happy-dom 下需要完整的 provider/teleport 环境；
// 这里只关心「关闭时机」，故把外壳替换为渲染默认插槽的哑组件。
const DialogStub = {
  name: 'Dialog',
  props: ['open'],
  emits: ['update:open'],
  template: '<div class="dialog-stub"><template v-if="open"><slot /></template></div>'
}

const PassThroughStub = (name: string) => ({
  name,
  template: '<div><slot /></div>'
})

const ButtonStub = {
  name: 'Button',
  props: ['variant', 'size', 'disabled'],
  template: '<button :disabled="disabled" v-bind="$attrs"><slot /></button>'
}

function mountDialog(onConfirm: () => Promise<unknown> | unknown) {
  return mount(AdminConfirmDialog, {
    props: { open: true, onConfirm },
    global: {
      stubs: {
        Dialog: DialogStub,
        DialogContent: PassThroughStub('DialogContent'),
        DialogHeader: PassThroughStub('DialogHeader'),
        DialogTitle: PassThroughStub('DialogTitle'),
        DialogDescription: PassThroughStub('DialogDescription'),
        DialogFooter: PassThroughStub('DialogFooter'),
        Button: ButtonStub
      }
    }
  })
}

/** 取主按钮（footer 内第二个 button；第一个是「取消」） */
function confirmButton(wrapper: ReturnType<typeof mountDialog>) {
  const buttons = wrapper.findAll('button')
  return buttons[buttons.length - 1]!
}

function deferred() {
  let resolve!: (v: unknown) => void
  let reject!: (e: unknown) => void
  const promise = new Promise<unknown>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('AdminConfirmDialog', () => {
  it('执行成功后请求关闭弹窗', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined)
    const wrapper = mountDialog(onConfirm)

    await confirmButton(wrapper).trigger('click')
    await nextTick()

    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false])
  })

  it('执行失败时保持打开，让调用方可重试', async () => {
    const onConfirm = vi.fn().mockRejectedValue(new Error('boom'))
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mountDialog(onConfirm)

    await confirmButton(wrapper).trigger('click')
    await nextTick()

    expect(spy).toHaveBeenCalled()
    expect(wrapper.emitted('update:open')).toBeUndefined()
    spy.mockRestore()
  })

  it('执行期间重复点击不再触发回调，结束后恢复可点', async () => {
    const { promise, resolve } = deferred()
    const onConfirm = vi.fn().mockReturnValue(promise)
    const wrapper = mountDialog(onConfirm)

    await confirmButton(wrapper).trigger('click')
    await nextTick()
    expect(confirmButton(wrapper).attributes('disabled')).toBeDefined()

    await confirmButton(wrapper).trigger('click')
    expect(onConfirm).toHaveBeenCalledTimes(1)

    resolve(undefined)
    await promise
    await nextTick()

    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false])
  })
})
