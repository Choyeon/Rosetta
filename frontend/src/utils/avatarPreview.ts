export type AvatarSource = "auto" | "custom" | "github" | "qq" | "gravatar";

export interface AvatarPreviewInput {
	avatar_source?: AvatarSource;
	avatar?: string | null;
	github?: string | null;
	qq?: string | null;
	email?: string | null;
}

export interface GuestProfile {
	name: string;
	email: string;
	website: string;
	qq: string;
	github: string;
	savedAt: number;
}

export const GUEST_PROFILE_KEY = "rosetta.guest_profile.v1";
export const GUEST_PROFILE_TTL_MS = 30 * 86400 * 1000;

const GITHUB_USERNAME_RE = /^[a-zA-Z0-9](?:-?[a-zA-Z0-9]){0,38}$/;
const QQ_RE = /^\d{5,11}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const WEBSITE_URL_RE = /^https?:\/\/[^\s]+$/i;

export function normalizeGithub(raw: string | null | undefined): string | null {
	if (!raw) return null;
	let s = raw.trim().replace(/\/$/, "");
	if (
		s.startsWith("http://github.com/") ||
		s.startsWith("https://github.com/") ||
		s.startsWith("//github.com/")
	) {
		s = s.split("github.com/")[1] ?? "";
	}
	if (s.startsWith("@")) s = s.slice(1);
	s = s.replace(/\/$/, "").trim();
	return GITHUB_USERNAME_RE.test(s) ? s : null;
}

export function normalizeQQ(raw: string | null | undefined): string | null {
	if (!raw) return null;
	const s = raw.trim();
	return QQ_RE.test(s) ? s : null;
}

export function normalizeEmail(raw: string | null | undefined): string | null {
	if (!raw) return null;
	const s = raw.trim();
	return EMAIL_RE.test(s) ? s : null;
}

const K = [
	0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee, 0xf57c0faf, 0x4787c62a,
	0xa8304613, 0xfd469501, 0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
	0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821, 0xf61e2562, 0xc040b340,
	0x265e5a51, 0xe9b6c7aa, 0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
	0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed, 0xa9e3e905, 0xfcefa3f8,
	0x676f02d9, 0x8d2a4c8a, 0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
	0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70, 0x289b7ec6, 0xeaa127fa,
	0xd4ef3085, 0x04881d05, 0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
	0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039, 0x655b59c3, 0x8f0ccc92,
	0xffeff47d, 0x85845dd1, 0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
	0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391,
];
const S = [
	[7, 12, 17, 22],
	[5, 9, 14, 20],
	[4, 11, 16, 23],
	[6, 10, 15, 21],
];
function safeAdd(x: number, y: number): number {
	const l = (x & 0xffff) + (y & 0xffff);
	return (((x >> 16) + (y >> 16) + (l >> 16)) << 16) | (l & 0xffff);
}
function leftRotate(x: number, n: number): number {
	return (x << n) | (x >>> (32 - n));
}
function toHex(n: number): string {
	let s = "";
	for (let i = 0; i < 4; i++)
		s +=
			((n >> (i * 8 + 4)) & 0x0f).toString(16) +
			((n >> (i * 8)) & 0x0f).toString(16);
	return s;
}
function utf8Bytes(s: string): number[] {
	const out: number[] = [];
	for (let i = 0; i < s.length; i++) {
		const c = s.charCodeAt(i);
		if (c < 0x80) {
			out.push(c);
		} else if (c < 0x800) {
			out.push(0xc0 | (c >> 6));
			out.push(0x80 | (c & 0x3f));
		} else if (c < 0xd800 || c >= 0xe000) {
			out.push(0xe0 | (c >> 12));
			out.push(0x80 | ((c >> 6) & 0x3f));
			out.push(0x80 | (c & 0x3f));
		} else {
			i++;
			const c2 = s.charCodeAt(i);
			const cp = 0x10000 + (((c & 0x3ff) << 10) | (c2 & 0x3ff));
			out.push(0xf0 | (cp >> 18));
			out.push(0x80 | ((cp >> 12) & 0x3f));
			out.push(0x80 | ((cp >> 6) & 0x3f));
			out.push(0x80 | (cp & 0x3f));
		}
	}
	return out;
}

export function md5HexStrict(s: string): string {
	const bytes = utf8Bytes(s);
	const n = bytes.length;
	const words: number[] = [];
	for (let i = 0; i < n; i++) words[i >> 2] |= bytes[i] << ((i % 4) * 8);
	const padLen = (((n + 8) >> 6) + 1) * 16;
	words.length = padLen;
	words[n >> 2] |= 0x80 << ((n % 4) * 8);
	words[padLen - 2] = (n * 8) | 0;
	words[padLen - 1] = Math.floor((n * 8) / 0x1_0000_0000) | 0;
	let h0 = 0x67452301;
	let h1 = 0xefcdab89;
	let h2 = 0x98badcfe;
	let h3 = 0x10325476;
	for (let off = 0; off < padLen; off += 16) {
		let a = h0;
		let b = h1;
		let c = h2;
		let d = h3;
		for (let step = 0; step < 64; step++) {
			const round = Math.floor(step / 16);
			const sh = S[round][step % 4];
			let f: number;
			let g: number;
			if (round === 0) {
				f = (b & c) | (~b & d);
				g = step;
			} else if (round === 1) {
				f = (b & d) | (c & ~d);
				g = (5 * step + 1) % 16;
			} else if (round === 2) {
				f = b ^ c ^ d;
				g = (3 * step + 5) % 16;
			} else {
				f = c ^ (b | ~d);
				g = (7 * step) % 16;
			}
			const temp = d;
			d = c;
			c = b;
			b = safeAdd(
				b,
				leftRotate(
					safeAdd(safeAdd(a, f), safeAdd(K[step], words[off + g])),
					sh,
				),
			);
			a = temp;
		}
		h0 = safeAdd(h0, a);
		h1 = safeAdd(h1, b);
		h2 = safeAdd(h2, c);
		h3 = safeAdd(h3, d);
	}
	return toHex(h0) + toHex(h1) + toHex(h2) + toHex(h3);
}

export function md5Hex(input: string): string {
	return md5HexStrict(input);
}

export function gravatarUrl(
	email: string | null | undefined,
	size = 160,
): string | null {
	const e = normalizeEmail(email);
	if (!e) return null;
	const digest = md5Hex(e.toLowerCase());
	return `https://www.gravatar.com/avatar/${digest}?s=${size}&d=mp&r=g`;
}

export function previewAvatarUrl(
	inp: AvatarPreviewInput,
	size = 160,
): string | null {
	const src: AvatarSource = inp.avatar_source ?? "auto";
	const customAvatar = WEBSITE_URL_RE.test(String(inp.avatar ?? ""))
		? String(inp.avatar)
		: null;
	const gh = normalizeGithub(inp.github);
	const qq = normalizeQQ(inp.qq);
	if (src === "custom") return customAvatar;
	if (src === "github")
		return gh ? `https://github.com/${gh}.png?size=${size}` : null;
	if (src === "qq")
		return qq
			? `https://q1.qlogo.cn/g?b=qq&nk=${qq}&s=${Math.min(640, Math.max(1, size))}`
			: null;
	if (src === "gravatar") return gravatarUrl(inp.email, size);
	if (customAvatar) return customAvatar;
	if (gh) return `https://github.com/${gh}.png?size=${size}`;
	if (qq)
		return `https://q1.qlogo.cn/g?b=qq&nk=${qq}&s=${Math.min(640, Math.max(1, size))}`;
	return gravatarUrl(inp.email, size) ?? null;
}

export function saveGuestProfile(p: GuestProfile) {
	try {
		localStorage.setItem(GUEST_PROFILE_KEY, JSON.stringify(p));
	} catch {
		/* ignore quota */
	}
}
export function loadGuestProfile(): GuestProfile | null {
	try {
		const raw = localStorage.getItem(GUEST_PROFILE_KEY);
		if (!raw) return null;
		const p = JSON.parse(raw) as GuestProfile;
		if (!p || typeof p.savedAt !== "number") return null;
		if (Date.now() - p.savedAt > GUEST_PROFILE_TTL_MS) {
			localStorage.removeItem(GUEST_PROFILE_KEY);
			return null;
		}
		return p;
	} catch {
		return null;
	}
}
export function clearGuestProfile() {
	try {
		localStorage.removeItem(GUEST_PROFILE_KEY);
	} catch {}
}
