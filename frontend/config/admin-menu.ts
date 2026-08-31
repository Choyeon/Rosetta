/**
 * 后台侧边栏与面包屑的单一数据源。
 * 所有后台页面、侧边栏、顶栏面包屑都从此读取，避免硬编码菜单导致的
 * 路由与菜单不同步（如之前的 /admin/roles 死链问题）。
 *
 * 图标使用 lucide-vue-next 组件；如需新增菜单项，在此处添加即可，
 * 侧边栏与面包屑会自动同步。
 */
import {
  LayoutDashboard,
  FileText,
  FolderTree,
  Tags,
  Layers,
  FileStack,
  MessageSquare,
  MessageCircle,
  Megaphone,
  Activity as ActivityIcon,
  Users,
  Award,
  Image as ImageIcon,
  Images,
  Settings,
  Menu as MenuIcon,
  Link2,
  Webhook,
  Download,
  Search,
  Languages,
  Gauge,
  ScrollText,
  Database,
  Trash2,
  Puzzle,
  Brush,
  BookOpen
} from '@lucide/vue'

import type { Component } from 'vue'

export interface AdminMenuItem {
  /** 路由路径，与 pages/admin 文件路由对应 */
  path: string
  /** 菜单显示名 */
  label: string
  /** lucide 图标组件 */
  icon: Component
  /** 可选徽标（如数量） */
  badge?: string | number
}

export interface AdminMenuGroup {
  key: string
  label: string
  items: AdminMenuItem[]
}

export const adminMenu: AdminMenuGroup[] = [
  {
    key: 'overview',
    label: '概览',
    items: [
      { path: '/admin', label: '仪表盘', icon: LayoutDashboard }
    ]
  },
  {
    key: 'content',
    label: '内容',
    items: [
      { path: '/admin/content/posts', label: '文章', icon: FileText },
      { path: '/admin/content/categories', label: '分类', icon: FolderTree },
      { path: '/admin/content/tags', label: '标签', icon: Tags },
      { path: '/admin/content/series', label: '系列', icon: Layers },
      { path: '/admin/content/pages', label: '页面', icon: FileStack }
    ]
  },
  {
    key: 'interaction',
    label: '互动',
    items: [
      { path: '/admin/interaction/comments', label: '评论', icon: MessageSquare },
      { path: '/admin/interaction/guestbook', label: '留言板', icon: MessageCircle },
      { path: '/admin/interaction/announcements', label: '公告', icon: Megaphone },
      { path: '/admin/interaction/activities', label: '动态', icon: ActivityIcon }
    ]
  },
  {
    key: 'users',
    label: '用户',
    items: [
      { path: '/admin/users', label: '用户管理', icon: Users },
      { path: '/admin/users/titles', label: '头衔', icon: Award }
    ]
  },
  {
    key: 'media',
    label: '媒体',
    items: [
      { path: '/admin/media/library', label: '媒体库', icon: ImageIcon },
      { path: '/admin/media/gallery', label: '相册', icon: Images }
    ]
  },
  {
    key: 'system',
    label: '系统',
    items: [
      { path: '/admin/system/settings', label: '站点设置', icon: Settings },
      { path: '/admin/system/themes', label: '主题平台', icon: Brush },
      { path: '/admin/system/plugins', label: '插件管理', icon: Puzzle },
      { path: '/admin/system/navigation', label: '导航菜单', icon: MenuIcon },
      { path: '/admin/system/friendlinks', label: '友情链接', icon: Link2 },
      { path: '/admin/system/webhooks', label: 'Webhook', icon: Webhook }
    ]
  },
  {
    key: 'tools',
    label: '工具',
    items: [
      { path: '/admin/tools/import-export', label: '导入导出', icon: Download },
      { path: '/admin/tools/seo', label: 'SEO', icon: Search },
      { path: '/admin/tools/translate', label: '翻译', icon: Languages },
      { path: '/admin/tools/performance', label: '性能', icon: Gauge },
      { path: '/admin/tools/audit-logs', label: '审计日志', icon: ScrollText },
      { path: '/admin/tools/migrations', label: '数据库迁移', icon: Database },
      { path: '/admin/tools/cache', label: '缓存管理', icon: Trash2 }
    ]
  },
  {
    key: 'docs',
    label: '开发文档',
    items: [
      { path: '/admin/docs/index', label: '开发文档', icon: BookOpen }
    ]
  }
]

/** 扁平化所有菜单项，便于面包屑 / 高亮匹配 */
export const adminMenuFlat: AdminMenuItem[] = adminMenu.flatMap(g => g.items)

/** 根据路径查找菜单项（精确匹配） */
export function findMenuItem(path: string): AdminMenuItem | undefined {
  return adminMenuFlat.find(item => item.path === path)
}

/** 根据路径查找所属分组 */
export function findMenuGroup(path: string): AdminMenuGroup | undefined {
  return adminMenu.find(g => g.items.some(item => item.path === path))
}
