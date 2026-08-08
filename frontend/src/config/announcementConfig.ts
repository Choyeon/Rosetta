import type { AnnouncementConfig } from "../types/announcementConfig";

export const announcementConfig: AnnouncementConfig = {
	// 公告标题：仅作为前端 fallback；如后端已设置公告（/api/announcements）或后台已写死标题，这里不会生效。
	// 为避免语言切换时 fallback 文本保持中文，Announcement.astro fallback 渲染用
	// t(I18nKey.announcement) 动态翻译，不再读取此处硬编码 title。
	title: "",

	// 公告内容：仅为本地 fallback；生产环境请在后台「公告管理」创建真实公告，
	// 真实公告会自动启用 i18n 多语言（title/content 为 JSON 对象）。
	content: "",

	// 是否允许用户关闭公告
	closable: true,

	link: {
		// 启用链接
		enable: true,
		// 链接文本：运行时通过 tSSR(announcementLearnMore) 翻译，此处留空避免硬编码中文
		text: "",
		// 链接 URL
		url: "/about/",
		// 内部链接
		external: false,
	},
	// 内部扩展字段：fallback 模式下的 i18n key 标识字符串（供 Announcement.astro 读取）
	// 使用字符串而不是 import I18nKey enum，避免 astro check 阶段 @i18n 别名解析异常
	__fallbackI18nKeys: {
		contentPlaceholder: "announcementContentPlaceholder",
		linkText: "announcementLearnMore",
	} as const,
};
