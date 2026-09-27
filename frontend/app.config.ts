/**
 * Nuxt app 级配置：只提供 shadcn-vue 取色用的色名（primary/neutral）。
 * 运行时 CSS 变量的真源是 assets/css/main.css 的 @theme/:root（tailwind.config.ts 未被加载），
 * 改配色请先改 main.css；本文件必须与之保持同一色名，否则会出现第二真源漂移。
 */
export default defineAppConfig({
  ui: {
    colors: {
      primary: 'sky',
      neutral: 'slate'
    }
  }
})
