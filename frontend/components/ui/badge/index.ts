import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

export { default as Badge } from './Badge.vue'

export const badgeVariants = cva(
  'inline-flex gap-1 items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        outline: 'text-foreground',
        /* 语义状态色配对铁律：
           -muted 背景 必须配 -muted-foreground 文字。
           -foreground 是给「实心填充」（bg-info / bg-warning）用的，
           放在 -muted 上会出现「浅色主题白底白字 / 深色主题黑底黑字」的隐形文本。 */
        info: 'border-transparent bg-info-muted text-info-muted-foreground',
        warning: 'border-transparent bg-warning-muted text-warning-muted-foreground',
        success: 'border-transparent bg-success-muted text-success-muted-foreground',
        error: 'border-transparent bg-error-muted text-error-muted-foreground'
      }
    },
    defaultVariants: {
      variant: 'default'
    }
  }
)

export type BadgeVariants = VariantProps<typeof badgeVariants>
