/**
 * Choyeon 系列站点（页脚友情链接）清单。
 *
 * 与 choyeon-video / Choyeon-Music / Choyeon-Book 三仓 web/src/family.js 里的
 * NETWORK_SITES 同名同值、同顺序；改域名必须四处一起改（三仓 family.js、本文件、
 * 以及 choyeon-video/backend/server.js 里给爬虫的 FAMILY_SITES 快照）。
 *
 * 与 /friends 页分工：那张卡片网格是后台可维护的公开友链（GET /friend-links），
 * 这里是同一个人名下自有的线上站，静态写死，不随后台开关或请求失败而消失。
 * apps 门户的 APP 列表已经列全项目，自身不挂这条链接，但仍是这里的链接目标。
 */
export interface NetworkSite {
  id: string
  name: string
  short: string
  url: string
  desc: string
}

export const NETWORK_SITES: NetworkSite[] = [
  { id: 'apps', name: 'Choyeon 应用集', short: '应用', url: 'https://apps.choyeon.cc', desc: '全部项目 · 展示与下载' },
  { id: 'music', name: 'Choyeon Music', short: '音乐', url: 'https://music.choyeon.cc', desc: '聚音乐 · 跨源搜索与沉浸歌词' },
  { id: 'book', name: 'Choyeon Book', short: '读书', url: 'https://book.choyeon.cc', desc: '阅读与听书 · 网文书架' },
  { id: 'video', name: 'ChonChon 影视', short: '影视', url: 'https://video.choyeon.cc', desc: '影视聚合 · 榜单与索引' },
  { id: 'rosetta', name: 'Rosetta 博客', short: '博客', url: 'https://choyeon.cc', desc: '自托管博客 · 主题与插件' }
]

/** 本站是 choyeon.cc（rosetta）：页脚只列别的站点，不给自己发链接。 */
export const OTHER_NETWORK_SITES: NetworkSite[] = NETWORK_SITES.filter(s => s.id !== 'rosetta')
