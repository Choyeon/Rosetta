import { describe, expect, it } from 'vitest'
import {
  PASSWORD_MIN_LENGTH,
  evaluatePasswordStrength,
  passwordStrengthPercent
} from '~~/lib/passwordStrength'

describe('evaluatePasswordStrength', () => {
  it('空口令不得报"强"，且所有规则都未通过', () => {
    const s = evaluatePasswordStrength('')
    expect(s.score).toBe(0)
    expect(s.level).toBe('weak')
    expect(s.rules.every(r => !r.passed)).toBe(true)
  })

  it('null / undefined 按空串处理（表单初值可能是 null）', () => {
    expect(evaluatePasswordStrength(null)).toEqual(evaluatePasswordStrength(''))
    expect(evaluatePasswordStrength(undefined)).toEqual(evaluatePasswordStrength(''))
  })

  it('只满足长度时是 weak（score=1）', () => {
    // 纯符号 8 位：只过长度，大小写与数字都没有（用纯数字会顺带过掉 digit 规则）
    const s = evaluatePasswordStrength('!@#$%^&*')
    expect(s.score).toBe(1)
    expect(s.level).toBe('weak')
    expect(s.rules.find(r => r.id === 'length')?.passed).toBe(true)
    expect(s.rules.find(r => r.id === 'upper')?.passed).toBe(false)
    expect(s.rules.find(r => r.id === 'digit')?.passed).toBe(false)
  })

  it('长度 + 小写 → fair（score=2，弱口令清单未命中）', () => {
    const s = evaluatePasswordStrength('abcdefgh')
    expect(s.score).toBe(2)
    expect(s.level).toBe('fair')
  })

  it('大小写 + 数字 → good（score=3，缺第四项长度之外都齐了）', () => {
    // 7 位：长度不过，大小写+数字过 → 3 分
    const s = evaluatePasswordStrength('Abcde1')
    expect(s.score).toBe(3)
    expect(s.level).toBe('good')
    expect(s.rules.find(r => r.id === 'length')?.passed).toBe(false)
  })

  it('四规则全满足 → strong', () => {
    const s = evaluatePasswordStrength('Rosetta2026')
    expect(s.score).toBe(4)
    expect(s.level).toBe('strong')
  })

  it('命中弱口令清单时整体归零 —— 其它规则全绿也没意义', () => {
    // "Password123" 满足长度 + 大小写 + 数字，但它是最高频的弱口令之一
    const s = evaluatePasswordStrength('Password123')
    expect(s.score).toBe(0)
    expect(s.level).toBe('weak')
    expect(s.rules.find(r => r.id === 'blocklist')?.passed).toBe(false)
  })

  it('弱口令命中后返回的规则清单仍要逐条标出通过项（UI 要画勾选态）', () => {
    const s = evaluatePasswordStrength('password123')
    expect(s.rules).toHaveLength(5)
    expect(s.rules.find(r => r.id === 'length')?.passed).toBe(true)
    expect(s.rules.find(r => r.id === 'digit')?.passed).toBe(true)
  })

  it('PASSWORD_MIN_LENGTH 与后端 oobe_constants 一致（8）', () => {
    expect(PASSWORD_MIN_LENGTH).toBe(8)
  })
})

describe('passwordStrengthPercent', () => {
  it('按 score/4 线性映射', () => {
    expect(passwordStrengthPercent(evaluatePasswordStrength(''))).toBe(0)
    expect(passwordStrengthPercent(evaluatePasswordStrength('!@#$%^&*'))).toBe(25)
    expect(passwordStrengthPercent(evaluatePasswordStrength('abcdefgh'))).toBe(50)
    expect(passwordStrengthPercent(evaluatePasswordStrength('Abcde1'))).toBe(75)
    expect(passwordStrengthPercent(evaluatePasswordStrength('Rosetta2026'))).toBe(100)
  })

  it('取值恒在 0–100 之间（进度条 width 越界会撑破布局）', () => {
    for (const pw of ['', 'a', 'abcdefgh', 'Abcdefg1', 'Password123']) {
      const p = passwordStrengthPercent(evaluatePasswordStrength(pw))
      expect(p).toBeGreaterThanOrEqual(0)
      expect(p).toBeLessThanOrEqual(100)
    }
  })
})
