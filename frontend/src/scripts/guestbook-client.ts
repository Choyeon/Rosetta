// @ts-nocheck
// ======== Inline avatar helpers（与 utils/avatarPreview.ts 保持一致的简化版，仅预览用） ========
const GB_K = [
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
const GB_S = [
	[7, 12, 17, 22],
	[5, 9, 14, 20],
	[4, 11, 16, 23],
	[6, 10, 15, 21],
];
function gbSafeAdd(x, y) {
	const l = (x & 0xffff) + (y & 0xffff);
	return (((x >> 16) + (y >> 16) + (l >> 16)) << 16) | (l & 0xffff);
}
function gbLeftRotate(x, n) {
	return (x << n) | (x >>> (32 - n));
}
function gbToHex(n) {
	let s = "";
	for (let i = 0; i < 4; i++)
		s +=
			((n >> (i * 8 + 4)) & 0x0f).toString(16) +
			((n >> (i * 8)) & 0x0f).toString(16);
	return s;
}
function gbUtf8Bytes(s) {
	const out = [];
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
function gbMd5Hex(s) {
	const bytes = gbUtf8Bytes(s);
	const n = bytes.length;
	const words = [];
	for (let i = 0; i < n; i++)
		words[i >> 2] = (words[i >> 2] || 0) | (bytes[i] << ((i % 4) * 8));
	const padLen = (((n + 8) >> 6) + 1) * 16;
	words.length = padLen;
	for (let i = 0; i < padLen; i++) words[i] = words[i] || 0;
	words[n >> 2] |= 0x80 << ((n % 4) * 8);
	words[padLen - 2] = (n * 8) | 0;
	words[padLen - 1] = Math.floor((n * 8) / 0x100000000) | 0;
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
			const sh = GB_S[round][step % 4];
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
			b = gbSafeAdd(
				b,
				gbLeftRotate(
					gbSafeAdd(gbSafeAdd(a, f), gbSafeAdd(GB_K[step], words[off + g])),
					sh,
				),
			);
			a = temp;
		}
		h0 = gbSafeAdd(h0, a);
		h1 = gbSafeAdd(h1, b);
		h2 = gbSafeAdd(h2, c);
		h3 = gbSafeAdd(h3, d);
	}
	return gbToHex(h0) + gbToHex(h1) + gbToHex(h2) + gbToHex(h3);
}
const GB_GITHUB_RE =
	/^(https?:\/\/github\.com\/|@)?[a-zA-Z0-9](?:-?[a-zA-Z0-9]){0,38}\/?$/;
function gbNormGithub(raw) {
	if (!raw) return null;
	let s = String(raw).trim().replace(/\/$/, "");
	if (
		s.startsWith("http://github.com/") ||
		s.startsWith("https://github.com/") ||
		s.startsWith("//github.com/")
	)
		s = s.split("github.com/")[1] ?? "";
	if (s.startsWith("@")) s = s.slice(1);
	s = s.replace(/\/$/, "").trim();
	return GB_GITHUB_RE.test(`@${s}`) ? s : null;
}
function gbNormQQ(raw) {
	if (!raw) return null;
	const s = String(raw).trim();
	return /^\d{5,11}$/.test(s) ? s : null;
}
function gbNormEmail(raw) {
	if (!raw) return null;
	const s = String(raw).trim();
	return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) ? s : null;
}
function gbGravatar(email, size) {
	const e = gbNormEmail(email);
	if (!e) return null;
	return (
		"https://www.gravatar.com/avatar/" +
		gbMd5Hex(e.toLowerCase()) +
		"?s=" +
		(size || 160) +
		"&d=mp&r=g"
	);
}
function gbPreviewAvatar({ github, qq, email }) {
	const gh = gbNormGithub(github);
	if (gh) return `https://github.com/${gh}.png?size=160`;
	const q = gbNormQQ(qq);
	if (q) return `https://q1.qlogo.cn/g?b=qq&nk=${q}&s=160`;
	return gbGravatar(email, 160) || null;
}
const GB_LS_KEY = "rosetta.guest_profile.v1";
const GB_LS_TTL = 30 * 86400 * 1000;
function gbSaveProfile(p) {
	try {
		localStorage.setItem(GB_LS_KEY, JSON.stringify(p));
	} catch {}
}
function gbLoadProfile() {
	try {
		const raw = localStorage.getItem(GB_LS_KEY);
		if (!raw) return null;
		const p = JSON.parse(raw);
		if (
			!p ||
			typeof p.savedAt !== "number" ||
			Date.now() - p.savedAt > GB_LS_TTL
		) {
			localStorage.removeItem(GB_LS_KEY);
			return null;
		}
		return p;
	} catch {
		return null;
	}
}
(function gbInitFormFromLS() {
	const p = gbLoadProfile();
	if (!p) return;
	const f = (id) => document.getElementById(id);
	if (f("gb-author")) f("gb-author").value = p.name || "";
	if (f("gb-email")) f("gb-email").value = p.email || "";
	if (f("gb-website")) f("gb-website").value = p.website || "";
	if (f("gb-qq")) f("gb-qq").value = p.qq || "";
	if (f("gb-github")) f("gb-github").value = p.github || "";
	setTimeout(gbUpdateAvatarPreview, 0);
})();
function gbUpdateAvatarPreview() {
	const f = (id) => document.getElementById(id);
	const img = document.getElementById("gb-avatar-preview");
	if (!img) return;
	const url = gbPreviewAvatar({
		github: f("gb-github")?.value,
		qq: f("gb-qq")?.value,
		email: f("gb-email")?.value,
	});
	const old = img.getAttribute("src");
	const next = url || "/favicon/rosetta-256.png";
	if (old !== next) {
		img.setAttribute("src", next);
		img.style.display = "";
	}
}
document.addEventListener("input", (e) => {
	const t = e.target;
	if (
		t &&
		typeof t.id === "string" &&
		/^gb-(author|email|website|qq|github)$/.test(t.id)
	) {
		gbUpdateAvatarPreview();
	}
});

// ======== Inline helpers end ========
import type { GuestbookEntry as GB } from "@/api/site";
import {
	createGuestbookEntry,
	getGuestbookEntries,
	likeGuestbookEntry,
} from "@/api/site";

const PAGE_SZ = 20;
let currentPage = 1;
const initialEl = document.getElementById("gb-total");
const initialVal = initialEl
	? Number.parseInt(initialEl.textContent || "0", 10)
	: 0;
let totalItems = Number.isFinite(initialVal) ? initialVal : 0;

function cardHtml(e: GB): string {
	const authorWebsite = e.author_website;
	const websiteLabel = authorWebsite
		? authorWebsite.replace(/^https?:\/\//, "").replace(/\/$/, "")
		: "";
	const badges: string[] = [];
	if (e.is_pinned) badges.push(`<span class="badge badge-pin">📌 置顶</span>`);
	if (e.is_featured)
		badges.push(`<span class="badge badge-featured">⭐ 精华</span>`);
	if (e.status === "pending")
		badges.push(`<span class="badge badge-pending">待审核</span>`);
	else if (e.status === "rejected")
		badges.push(`<span class="badge badge-rejected">已拒绝</span>`);
	else if (e.status === "spam")
		badges.push(`<span class="badge badge-spam">垃圾</span>`);
	const content = renderHtml(e.content);
	return `
		<div class="gb-card p-4 sm:p-5 rounded-2xl transition-all duration-200" data-id="${e.id}">
			<div class="flex items-start gap-3.5">
				<img src="${(e as any).resolved_avatar_url || e.author_avatar || "/favicon/rosetta-256.png"}" alt="" loading="lazy" class="w-11 h-11 sm:w-12 sm:h-12 rounded-xl object-cover flex-shrink-0 border border-[var(--line-divider)] bg-neutral-100 dark:bg-neutral-800" />
				<div class="flex-1 min-w-0">
					<div class="flex flex-wrap items-start gap-x-2 gap-y-1.5 mb-2">
						<div class="flex items-center gap-2 min-w-0">
							<span class="font-semibold text-[0.95rem] text-neutral-900 dark:text-neutral-100 truncate max-w-[180px]">${escHtml(e.author_name)}</span>
							${
								authorWebsite
									? `<a href="${authorWebsite}" target="_blank" rel="noopener noreferrer" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline truncate max-w-[180px]">${escHtml(websiteLabel)}</a>`
									: ""
							}
						</div>
						<div class="flex flex-wrap items-center gap-1.5">${badges.join("")}</div>
					</div>
					<div class="gb-content text-[0.95rem] leading-relaxed text-neutral-800 dark:text-neutral-200 whitespace-pre-wrap break-words">${content}</div>
					<div class="mt-3 flex flex-wrap items-center justify-between gap-2">
						<span class="text-xs text-neutral-500 dark:text-neutral-400 font-mono tabular-nums">${fmtDate(e.created_at)}</span>
						<button class="gb-like-btn inline-flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400 hover:text-pink-500 dark:hover:text-pink-400 transition-colors py-1 px-2 rounded-lg hover:bg-pink-500/10" data-like-id="${e.id}">
							<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" data-like-icon="${e.id}"><path d="M20.84,4.61a5.5,5.5 0,0,0-7.78,0L12,5.67l-1.06-1.06a5.5,5.5 0,0,0-7.78,7.78l1.06,1.06L12,21.23l7.78-7.78,1.06-1.06a5.5,5.5 0,0,0,0-7.78z"/></svg>
							<span data-like-count="${e.id}">${e.likes_count}</span>
						</button>
					</div>
				</div>
			</div>
		</div>
	`;
}

function escHtml(s: string): string {
	return s
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}
function renderHtml(raw: string): string {
	let out = escHtml(raw);
	out = out.replace(
		/(https?:\/\/[^\s<]+)/g,
		(url) =>
			`<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-[var(--primary)] underline decoration-[color:var(--primary)]/30 hover:decoration-[color:var(--primary)] underline-offset-2 transition-all">${url.length > 60 ? `${url.slice(0, 58)}…` : url}</a>`,
	);
	return out;
}
function fmtDate(s: string): string {
	try {
		const d = new Date(s);
		const pad = (n: number) => n.toString().padStart(2, "0");
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
	} catch {
		return s;
	}
}
function emptyState(): string {
	return `
		<div class="py-14 flex flex-col items-center justify-center text-center">
			<div class="w-20 h-20 rounded-full bg-gradient-to-br from-cyan-100/60 to-sky-100/60 dark:from-cyan-500/10 dark:to-sky-500/10 flex items-center justify-center mb-4">
				<svg class="w-10 h-10 text-cyan-500 dark:text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.95,13.25a1,1 0,0,1-1,1h-4v4a1,1 0,0,1-1.7.71L8,14H4a1,1 0,0,1-1-1V5A1,1 0,0,1,4,4h12.82a2,2 0,0,1,1.41.59l2.18,2.18A2,2 0,0,1,21,8.59Z" transform="rotate(12 12 12)"/></svg>
			</div>
			<p class="text-base font-semibold text-neutral-800 dark:text-neutral-100 mb-1">成为第一个留言的人吧！</p>
			<p class="text-sm text-neutral-500 dark:text-neutral-400">在上方表单留下你的想法 💫</p>
		</div>
	`;
}
function showAlert(type: "success" | "error" | "info", msg: string) {
	const el = document.getElementById("gb-alert");
	if (!el) return;
	const cls =
		type === "success"
			? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-500/20"
			: type === "error"
				? "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400 border border-red-100 dark:border-red-500/20"
				: "bg-sky-50 text-sky-700 dark:bg-sky-500/10 dark:text-sky-400 border border-sky-100 dark:border-sky-500/20";
	el.className = `mt-3 p-3 rounded-xl text-sm flex items-start gap-2 ${cls}`;
	el.innerHTML = msg;
	el.classList.remove("hidden");
	if (type !== "error") {
		setTimeout(() => {
			el.classList.add("hidden");
		}, 5000);
	}
}

async function loadPage(page: number) {
	currentPage = page;
	const list = document.getElementById("gb-list") as HTMLElement;
	list.style.opacity = "0.4";
	try {
		const r = await getGuestbookEntries({
			page,
			page_size: PAGE_SZ,
			status: "approved",
		});
		const items: GB[] = r.items || [];
		totalItems = r.total || 0;
		const totalEl = document.getElementById("gb-total");
		if (totalEl) totalEl.textContent = String(totalItems);
		if (items.length === 0) {
			list.innerHTML = emptyState();
		} else {
			list.innerHTML = items.map((i) => cardHtml(i)).join("");
		}
		renderPagination();
		bindLikeButtons();
	} catch (err: any) {
		showAlert("error", `加载失败：${err?.message || "请稍后重试"}`);
	} finally {
		list.style.opacity = "1";
	}
}
function renderPagination() {
	const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SZ));
	const p = document.getElementById("gb-pagination") as HTMLElement;
	if (totalPages <= 1) {
		p.innerHTML = "";
		return;
	}
	let html = '<div class="flex items-center gap-1">';
	html += `<button class="page-btn ${currentPage === 1 ? "disabled" : ""}" id="gb-p-prev"><svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15,18 9,12 15,6"/></svg></button>`;
	for (let i = 1; i <= totalPages; i++) {
		html += `<button class="page-btn ${i === currentPage ? "active" : ""}" data-page="${i}">${i}</button>`;
	}
	html += `<button class="page-btn ${currentPage === totalPages ? "disabled" : ""}" id="gb-p-next"><svg style="width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9,18 15,12 9,6"/></svg></button>`;
	html += "</div>";
	p.innerHTML = html;
	p.querySelectorAll<HTMLButtonElement>("[data-page]").forEach((b) => {
		b.addEventListener("click", () => loadPage(Number(b.dataset.page)));
	});
	const prev = document.getElementById("gb-p-prev");
	const nxt = document.getElementById("gb-p-next");
	prev?.addEventListener(
		"click",
		() => currentPage > 1 && loadPage(currentPage - 1),
	);
	nxt?.addEventListener(
		"click",
		() => currentPage < totalPages && loadPage(currentPage + 1),
	);
}
function bindLikeButtons() {
	document
		.querySelectorAll<HTMLButtonElement>(".gb-like-btn")
		.forEach((btn) => {
			if ((btn as any)._bound) return;
			(btn as any)._bound = true;
			btn.addEventListener("click", async () => {
				const id = Number(btn.dataset.likeId);
				const countEl = document.querySelector<HTMLSpanElement>(
					`[data-like-count="${id}"]`,
				);
				const iconEl = document.querySelector<HTMLElement>(
					`[data-like-icon="${id}"]`,
				);
				try {
					const r = await likeGuestbookEntry(id);
					if (countEl && typeof r.likes_count === "number") {
						countEl.textContent = String(r.likes_count);
						if (iconEl) {
							iconEl.setAttribute("fill", "currentColor");
							iconEl.classList.add("text-pink-500", "dark:text-pink-400");
							btn.classList.add("text-pink-500", "dark:text-pink-400");
						}
					}
				} catch (err: any) {
					console.warn("like failed", err);
				}
			});
		});
}

function submitForm(ev: Event) {
	ev.preventDefault();
	const btn = document.getElementById("gb-submit") as HTMLButtonElement;
	const author = (
		document.getElementById("gb-author") as HTMLInputElement
	).value.trim();
	const email =
		(document.getElementById("gb-email") as HTMLInputElement).value.trim() ||
		undefined;
	const website =
		(document.getElementById("gb-website") as HTMLInputElement).value.trim() ||
		undefined;
	const qq =
		(document.getElementById("gb-qq") as HTMLInputElement).value.trim() ||
		undefined;
	const github =
		(document.getElementById("gb-github") as HTMLInputElement).value.trim() ||
		undefined;
	const content = (
		document.getElementById("gb-content") as HTMLTextAreaElement
	).value.trim();
	if (!author) {
		showAlert("error", "请填写昵称");
		return;
	}
	if (author.length < 2) {
		showAlert("error", "昵称至少 2 个字符");
		return;
	}
	if (content.length < 2) {
		showAlert("error", "留言内容至少 2 个字符");
		return;
	}
	btn.disabled = true;
	const oldHTML = btn.innerHTML;
	btn.innerHTML = `<svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21,12a9,9 0,1,1-6.22-8.56"/></svg><span>提交中…</span>`;
	createGuestbookEntry({
		author_name: author,
		author_email: email,
		author_website: website,
		content,
		qq,
		github,
		author_avatar_source: "auto",
	})
		.then((entry: GB) => {
			(document.getElementById("gb-content") as HTMLTextAreaElement).value = "";
			gbSaveProfile({
				name: author,
				email: email ?? "",
				website: website ?? "",
				qq: qq ?? "",
				github: github ?? "",
				savedAt: Date.now(),
			});
			gbUpdateAvatarPreview();
			if (entry.status === "approved") {
				showAlert("success", "留言提交成功！已显示在列表中。");
				loadPage(1);
			} else if (entry.status === "pending") {
				showAlert("info", "留言已提交，等待审核 💫 审核通过后将显示在列表中。");
			} else if (entry.status === "rejected") {
				showAlert("error", "留言内容触发敏感词被拒绝，请修改后重试。");
			} else {
				showAlert("info", "留言提交成功。");
			}
		})
		.catch((err: any) => {
			const m = err?.message || err?.error_code || "请稍后重试";
			showAlert("error", `提交失败：${m}`);
		})
		.finally(() => {
			btn.disabled = false;
			btn.innerHTML = oldHTML;
		});
}

document.getElementById("gb-form")?.addEventListener("submit", submitForm);
document
	.getElementById("gb-refresh")
	?.addEventListener("click", () => loadPage(currentPage));
bindLikeButtons();
