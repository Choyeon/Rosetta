export type AnnouncementConfig = {
	// enable属性已移除，现在通过sidebarLayoutConfig统一控制
	title?: string; // 公告栏标题
	content: string; // 公告栏内容
	icon?: string; // 公告栏图标
	type?: "info" | "warning" | "success" | "error"; // 公告类型
	closable?: boolean; // 是否可关闭
	link?: {
		enable: boolean; // 是否启用链接
		text: string; // 链接文字
		url: string; // 链接地址
		external?: boolean; // 是否外部链接
	};
	// 内部扩展字段：fallback 模式下使用的 i18n key 字符串（避免硬编码中英文切换时仍显示中文）
	// 使用字符串键名而非 enum import，规避 astro check 阶段对 @i18n 别名解析的异常
	__fallbackI18nKeys?: {
		contentPlaceholder?: string;
		linkText?: string;
	};
};
