import type { MusicPlayerConfig } from "../types/musicConfig";

// 音乐播放器配置 —— 注：所有运行时默认值均改为空，由后端设置统一控制
// （从 /api/core/config 返回 music_* 字段，经 dynamic-config.ts 合并后应用）
export const musicPlayerConfig: MusicPlayerConfig = {
	// 是否在导航栏显示音乐播放器入口
	showInNavbar: true,

	// 是否在侧边栏显示音乐播放器组件
	showInSidebar: true,

	// 使用方式："meting" 使用 Meting API，"local" 使用本地音乐列表
	mode: "meting",

	// 默认音量 (0-1)
	volume: 0.7,

	// 播放模式：'list'=列表循环, 'one'=单曲循环, 'random'=随机播放
	playMode: "list",

	// 是否显启用歌词
	showLyrics: true,

	// Meting API 配置 —— 默认使用公共 API，无需复制 cookie 即可使用
	// 仅需在管理后台填写歌单 ID 即可播放；如需切换私有 API 可在后台覆盖
	meting: {
		// Meting API 地址（默认公共 API，无需认证）
		api: "https://api.i-meto.com/meting/api?server=:server&type=:type&id=:id&r=:r",
		// 音乐平台：netease=网易云音乐, tencent=QQ音乐, kugou=酷狗音乐, xiami=虾米音乐, baidu=百度音乐
		server: "netease",
		// 类型：song=单曲, playlist=歌单, album=专辑, search=搜索, artist=艺术家
		type: "playlist",
		// 歌单/专辑/单曲 ID 或搜索关键词（默认置空，避免硬编码第三方歌单）
		id: "",
		// 认证 token（可选，公共 API 无需填写，无需复制 cookie）
		auth: "",
		// 备用 API 配置（当主 API 失败时自动切换，均为公共免认证 API）
		fallbackApis: [
			"https://api.injahow.cn/meting/?server=:server&type=:type&id=:id&r=:r",
		],
	},

	// 本地音乐配置（当 mode 为 'local' 时使用）
	local: {
		playlist: [],
	},
};
