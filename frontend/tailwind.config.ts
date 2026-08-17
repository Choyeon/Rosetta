import type { Config } from 'tailwindcss'
import tailwindcssAnimate from 'tailwindcss-animate'

export default {
  darkMode: ['class'],
  content: [
    './components/**/*.{vue,js,ts,jsx,tsx,mdx}',
    './app/**/*.{vue,js,ts,jsx,tsx,mdx}',
    './layouts/**/*.{vue,js,ts,jsx,tsx,mdx}',
    './pages/**/*.{vue,js,ts,jsx,tsx,mdx}',
    './plugins/**/*.{vue,js,ts,jsx,tsx,mdx}',
    './composables/**/*.{ts,vue}'
  ],
  prefix: '',
  theme: {
    container: {
      center: true,
      padding: '1.5rem',
      screens: {
        '2xl': '1280px'
      }
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))'
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))'
        },
        destructive: {
          'DEFAULT': 'hsl(var(--destructive))',
          'foreground': 'hsl(var(--destructive-foreground))',
          'muted': 'hsl(var(--destructive-muted))',
          'muted-foreground': 'hsl(var(--destructive-muted-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))'
        },
        sidebar: {
          'DEFAULT': 'hsl(var(--sidebar-background))',
          'foreground': 'hsl(var(--sidebar-foreground))',
          'primary': 'hsl(var(--sidebar-primary))',
          'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
          'accent': 'hsl(var(--sidebar-accent))',
          'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
          'border': 'hsl(var(--sidebar-border))',
          'ring': 'hsl(var(--sidebar-ring))'
        },
        /* ====== 全站统一语义状态色：info / success / warning / error ======
           颜色源定义在 app/assets/css/main.css 的 :root + .dark 中。
           tailwind 仅负责把 CSS 变量暴露为 class：
             → text-info / bg-info / border-info
             → text-success / bg-success-muted / text-success-foreground …
           改颜色只改 main.css 的 token，不要在单个文件里硬编码颜色。 */
        info: {
          'DEFAULT': 'hsl(var(--info))',
          'foreground': 'hsl(var(--info-foreground))',
          'muted': 'hsl(var(--info-muted))',
          'muted-foreground': 'hsl(var(--info-muted-foreground))'
        },
        success: {
          'DEFAULT': 'hsl(var(--success))',
          'foreground': 'hsl(var(--success-foreground))',
          'muted': 'hsl(var(--success-muted))',
          'muted-foreground': 'hsl(var(--success-muted-foreground))'
        },
        warning: {
          'DEFAULT': 'hsl(var(--warning))',
          'foreground': 'hsl(var(--warning-foreground))',
          'muted': 'hsl(var(--warning-muted))',
          'muted-foreground': 'hsl(var(--warning-muted-foreground))'
        },
        error: {
          'DEFAULT': 'hsl(var(--error))',
          'foreground': 'hsl(var(--error-foreground))',
          'muted': 'hsl(var(--error-muted))',
          'muted-foreground': 'hsl(var(--error-muted-foreground))'
        }
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      fontFamily: {
        sans: [
          'Geist',
          'Inter',
          'ui-sans-serif',
          'system-ui',
          'sans-serif'
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'monospace'
        ],
        display: ['Fraunces', 'ui-serif', 'Georgia', 'serif']
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--reka-accordion-content-height)' }
        },
        'accordion-up': {
          from: { height: 'var(--reka-accordion-content-height)' },
          to: { height: '0' }
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        'progress-stripe': {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '40px 0' }
        },
        'gradient-x': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.5s ease-out both',
        'progress-stripe': 'progress-stripe 1s linear infinite',
        'gradient-x': 'gradient-x 6s ease infinite'
      },
      boxShadow: {
        soft: '0 10px 30px -12px rgba(15, 23, 42, 0.12)',
        pop: '0 20px 50px -20px hsl(var(--primary) / 0.35)'
      }
    }
  },
  plugins: [tailwindcssAnimate]
} satisfies Config
