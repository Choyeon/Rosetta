// 时区暂时使用默认值
const siteConfig = { timezone: "Asia/Shanghai", lang: "zh_CN" };

/** 判断 Date 是否为有效时间 */
function isValidDate(d: Date | null | undefined): d is Date {
	return d instanceof Date && !Number.isNaN(d.getTime());
}

/** 尝试将任意输入解析为 Date，失败返回 null */
function tryParseDate(dateInput: unknown): Date | null {
	if (dateInput instanceof Date)
		return isValidDate(dateInput) ? dateInput : null;
	if (typeof dateInput === "number" && Number.isFinite(dateInput)) {
		const d = new Date(dateInput);
		return isValidDate(d) ? d : null;
	}
	if (typeof dateInput === "string" && dateInput.trim().length > 0) {
		// 处理 SQLite 常见格式：YYYY-MM-DD HH:mm:ss（缺少 T 会被某些浏览器解析失败）
		let s = dateInput.trim();
		if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?/.test(s)) {
			s = s.replace(" ", "T");
		}
		const d = new Date(s);
		if (isValidDate(d)) return d;
		// 兼容无分隔符或带时区后缀的其他形式
		const d2 = new Date(dateInput);
		return isValidDate(d2) ? d2 : null;
	}
	return null;
}

export function formatDateToYYYYMMDD(date: Date): string {
	const d = tryParseDate(date);
	if (!d) return "";
	return d.toISOString().substring(0, 10);
}

// 国际化日期格式化函数
export function formatDateI18n(
	dateInput: Date | string | null | undefined,
	includeTime?: boolean,
): string {
	const date = tryParseDate(dateInput);
	if (!date) return "";
	const lang = (siteConfig?.lang as string) || "en";

	// 根据语言设置不同的日期格式
	const options: Intl.DateTimeFormatOptions = {
		year: "numeric",
		month: "long",
		day: "numeric",
	};

	if (includeTime) {
		options.hour = "2-digit";
		options.minute = "2-digit";
		options.second = "2-digit";
	}

	// 如果配置了时区，则将其用于格式化（IANA 时区字符串）
	if (siteConfig?.timezone) {
		(options as Intl.DateTimeFormatOptions).timeZone = siteConfig.timezone;
	}

	// 语言代码映射
	const localeMap: Record<string, string> = {
		zh_CN: "zh-CN",
		zh_TW: "zh-TW",
		en: "en-US",
		ja: "ja-JP",
		es: "es-ES",
		th: "th-TH",
		vi: "vi-VN",
		tr: "tr-TR",
		id: "id-ID",
		fr: "fr-FR",
		de: "de-DE",
		ar: "ar-SA",
	};

	const locale = localeMap[lang] || "en-US";
	return includeTime
		? date.toLocaleString(locale, options)
		: date.toLocaleDateString(locale, options);
}

// 国际化日期时间格式化函数（带时分秒）
export function formatDateI18nWithTime(
	dateInput: Date | string | null | undefined,
): string {
	return formatDateI18n(dateInput, true);
}

export function formatDynamicDate(
	dateInput: Date | string | null | undefined,
): string {
	const date = tryParseDate(dateInput);
	if (!date) return "";
	const parts = new Intl.DateTimeFormat("en-CA", {
		timeZone: "UTC",
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
		hourCycle: "h23",
	}).formatToParts(date);
	const get = (type: Intl.DateTimeFormatPartTypes) =>
		parts.find((part) => part.type === type)?.value || "";
	return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get(
		"minute",
	)}:${get("second")}`;
}

export function formatTimezoneOffset(
	timezone: string,
	dateInput: Date | string | null | undefined,
): string {
	const date = tryParseDate(dateInput);
	if (!date) return "UTC";
	const timezoneName = new Intl.DateTimeFormat("en-US", {
		timeZone: timezone,
		timeZoneName: "longOffset",
	})
		.formatToParts(date)
		.find((part) => part.type === "timeZoneName")?.value;

	if (!timezoneName || timezoneName === "GMT") return "UTC";

	return timezoneName
		.replace("GMT", "UTC")
		.replace(/([+-])0(\d)/, "$1$2")
		.replace(":00", "");
}

// 统一格式为 YYYY-MM-DD HH:mm，支持站点时区
export function formatDateTimeToYYYYMMDDHHmm(
	dateInput: Date | string | null | undefined,
): string {
	const date = tryParseDate(dateInput);
	if (!date) return "";

	const options: Intl.DateTimeFormatOptions = {
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
		hour12: false,
	};

	if (siteConfig?.timezone) {
		options.timeZone = siteConfig.timezone;
	}

	const parts = new Intl.DateTimeFormat("en-CA", options).formatToParts(date);
	const get = (type: Intl.DateTimeFormatPartTypes) =>
		parts.find((p) => p.type === type)?.value || "";

	return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}
