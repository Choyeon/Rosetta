/**
 * 管理员密码强度评估 —— 纯函数，可被单测与任意 UI 复用。
 *
 * 口径对齐后端 `backend/core/password_policy.py::validate_password`：
 * 长度 ≥8、含小写、含大写、含数字、不在常见弱口令清单里。
 *
 * ⚠️ **本模块只做提示，不做最终闸门**。原因：后端这套规则受
 * `security_password_policy` 开关控制，前端拿不到该配置（也不该为它加一个公开端点）。
 * 若前端照抄规则硬拦，开关关闭的部署会被误挡；若前端不拦，开关打开的部署又会让用户
 * 填完一整页才在最后一步被拒。
 * 因此约定：**强度分与规则清单只用于可视化**，权威结论一律来自
 * `POST /oobe/preflight`（返回 `issues[].code === 'PASSWORD_WEAK'`）。
 *
 * 弱口令清单刻意只留最高频的一小撮：完整版在后端（约 70 条），
 * 前端不复制全量以免两边漂移后给出互相矛盾的提示。
 */

/** 规则条目：id 稳定，供 UI 渲染勾选态文案（文案本身走 i18n） */
export type PasswordRuleId = 'length' | 'lower' | 'upper' | 'digit' | 'blocklist'

export interface PasswordRuleState {
  id: PasswordRuleId
  passed: boolean
}

export interface PasswordStrength {
  /** 0–4：满足的规则数（blocklist 命中会把总分按 0 处理） */
  score: number
  /** weak(0-1) / fair(2) / good(3) / strong(4) */
  level: 'weak' | 'fair' | 'good' | 'strong'
  rules: PasswordRuleState[]
}

export const PASSWORD_MIN_LENGTH = 8

const TOP_WEAK_PASSWORDS: ReadonlySet<string> = new Set([
  '123456', 'password', '12345678', 'qwerty', 'abc123', '123456789',
  '111111', '1234567', 'admin', 'letmein', 'welcome', 'password123'
])

export function evaluatePasswordStrength(password: string | null | undefined): PasswordStrength {
  const pw = typeof password === 'string' ? password : ''

  // 空口令：所有规则一律未通过。
  // 否则 blocklist 那条（`!清单.has('')`）会被判成"通过"，UI 上出现一个
  // 什么都没输入就打勾的绿条目 —— 规则清单的意义是"你还差什么"，不是"你没犯什么错"。
  if (pw.length === 0) {
    return {
      score: 0,
      level: 'weak',
      rules: [
        { id: 'length', passed: false },
        { id: 'lower', passed: false },
        { id: 'upper', passed: false },
        { id: 'digit', passed: false },
        { id: 'blocklist', passed: false }
      ]
    }
  }

  const rules: PasswordRuleState[] = [
    { id: 'length', passed: pw.length >= PASSWORD_MIN_LENGTH },
    { id: 'lower', passed: /[a-z]/.test(pw) },
    { id: 'upper', passed: /[A-Z]/.test(pw) },
    { id: 'digit', passed: /\d/.test(pw) },
    { id: 'blocklist', passed: !TOP_WEAK_PASSWORDS.has(pw.toLowerCase()) }
  ]

  // 命中弱口令清单时直接归零：其它规则全绿也没意义（"Abc12345" 之类仍在清单外，
  // 但 "password123" 满足大小写+数字却是最典型的弱口令）。
  if (!rules[4]!.passed) {
    return { score: 0, level: 'weak', rules }
  }

  const score = rules.slice(0, 4).filter(r => r.passed).length
  const level = score <= 1 ? 'weak' : score === 2 ? 'fair' : score === 3 ? 'good' : 'strong'
  return { score, level, rules }
}

/** 进度条用：把 score 映射成百分比（0 分时给 8% 让条子仍可见，避免"空条"看起来像没渲染） */
export function passwordStrengthPercent(strength: PasswordStrength): number {
  if (strength.score <= 0) return 0
  return Math.round((strength.score / 4) * 100)
}
