<!--
  SharePoster — 文章分享海报生成器（canvas + qrcode）
  props: title / cover / author / avatar / excerpt / url / date
  点击"生成"按钮在 canvas 上绘制，然后可下载 PNG
-->
<script setup lang="ts">
import QRCode from "qrcode";

interface Props {
  title?: string;
  cover?: string;
  author?: string;
  avatar?: string;
  excerpt?: string;
  url?: string;
  date?: string;
  siteName?: string;
  width?: number;
  height?: number;
}
// 注意：defineProps 的默认工厂函数不能引用 script setup 内的局部变量
// （如 runtimeConfig / import.meta.client / dayjs），因为它们会被提升到 setup() 外。
// 所以这里仅用字面量占位，真正的动态兜底值在下方 props$ 里 computed 合并。
const props = withDefaults(defineProps<Props>(), {
  title: "未命名文章",
  cover: "",
  author: "Choyu Choyeon",
  avatar: "",
  excerpt: "这是文章摘要，点击下方按钮生成海报分享到社交平台。",
  url: "",
  date: "",
  siteName: "Rosetta",
  width: 720,
  height: 1080,
});

const runtimeConfig = useRuntimeConfig();
const IS_CLIENT = import.meta.client;

// 动态兜底合并
const p = computed(() => ({
  title: p.value.title,
  cover: p.value.cover,
  author: p.value.author,
  avatar: p.value.avatar,
  excerpt: p.value.excerpt,
  url: p.value.url || (IS_CLIENT ? window.location.href : ""),
  date: p.value.date || dayjs().format("YYYY-MM-DD"),
  siteName: p.value.siteName || runtimeConfig.public?.siteName || "Rosetta",
  width: p.value.width,
  height: p.value.height,
}));

const canvasEl = ref<HTMLCanvasElement | null>(null);
const generating = ref(false);
const generatedUrl = ref("");
const open = ref(false);

function drawRoundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth: number, lineHeight: number): number {
  const lines: string[] = [];
  let current = "";
  for (const ch of text) {
    const test = current + ch;
    if (ctx.measureText(test).width > maxWidth && current) {
      lines.push(current);
      current = ch;
    } else {
      current = test;
    }
  }
  if (current) lines.push(current);
  let yy = y;
  for (const line of lines) {
    ctx.fillText(line, x, yy);
    yy += lineHeight;
  }
  return yy;
}

async function generate() {
  const canvas = canvasEl.value;
  if (!canvas) return;
  generating.value = true;
  generatedUrl.value = "";
  try {
    canvas.width = p.value.width;
    canvas.height = p.value.height;
    const ctx = canvas.getContext("2d")!;
    // 背景
    const grd = ctx.createLinearGradient(0, 0, 0, p.value.height);
    grd.addColorStop(0, "#eef2ff");
    grd.addColorStop(0.5, "#ffffff");
    grd.addColorStop(1, "#fef3c7");
    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, p.value.width, p.value.height);
    // 装饰斑点
    ctx.fillStyle = "rgba(99,102,241,0.07)";
    for (let i = 0; i < 18; i++) {
      ctx.beginPath();
      ctx.arc(Math.random() * p.value.width, Math.random() * p.value.height, 20 + Math.random() * 60, 0, Math.PI * 2);
      ctx.fill();
    }
    // 顶部卡片背景
    drawRoundedRect(ctx, 40, 40, p.value.width - 80, p.value.height - 80, 28);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,0.05)";
    ctx.lineWidth = 1;
    ctx.stroke();
    // 封面图（如存在）
    let cursorY = 80;
    if (p.value.cover) {
      try {
        const cov = await new Promise<HTMLImageElement>((res, rej) => {
          const img = new Image();
          img.crossOrigin = "anonymous";
          img.onload = () => res(img);
          img.onerror = rej;
          img.src = p.value.cover;
        });
        drawRoundedRect(ctx, 80, cursorY, p.value.width - 160, 360, 20);
        ctx.save();
        ctx.clip();
        const ir = cov.width / cov.height;
        const tw = p.value.width - 160, th = 360;
        const tr = tw / th;
        let sw = cov.width, sh = cov.height, sx = 0, sy = 0;
        if (ir > tr) { sw = cov.height * tr; sx = (cov.width - sw) / 2; }
        else { sh = cov.width / tr; sy = (cov.height - sh) / 2; }
        ctx.drawImage(cov, sx, sy, sw, sh, 80, cursorY, tw, th);
        ctx.restore();
        cursorY += 380;
      } catch { /* ignore */ }
    }
    // 标题
    ctx.fillStyle = "#0f172a";
    ctx.font = "bold 38px -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif";
    cursorY = wrapText(ctx, p.value.title, 80, cursorY, p.value.width - 160, 50) + 20;
    // 分隔线
    ctx.strokeStyle = "#6366f1";
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(80, cursorY); ctx.lineTo(140, cursorY); ctx.stroke();
    cursorY += 20;
    // 摘要
    ctx.fillStyle = "rgba(15,23,42,0.65)";
    ctx.font = "22px -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif";
    cursorY = wrapText(ctx, p.value.excerpt, 80, cursorY, p.value.width - 160, 34) + 40;
    // 底部作者 + 二维码
    const bottomY = p.value.height - 180;
    // 头像
    const avatarSize = 80;
    const avatarX = 80;
    const avatarY = bottomY;
    try {
      const av = await new Promise<HTMLImageElement>((res, rej) => {
        if (!p.value.avatar) return rej("no avatar");
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => res(img);
        img.onerror = rej;
        img.src = p.value.avatar;
      });
      ctx.save();
      ctx.beginPath();
      ctx.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(av, avatarX, avatarY, avatarSize, avatarSize);
      ctx.restore();
    } catch {
      ctx.fillStyle = "#6366f1";
      ctx.beginPath();
      ctx.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.font = "bold 36px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(p.value.author).slice(0, 1).toUpperCase(), avatarX + avatarSize / 2, avatarY + avatarSize / 2 + 2);
      ctx.textAlign = "start";
      ctx.textBaseline = "alphabetic";
    }
    // 作者 + 日期
    ctx.fillStyle = "#0f172a";
    ctx.font = "bold 24px -apple-system, 'PingFang SC', sans-serif";
    ctx.fillText(p.value.author, avatarX + avatarSize + 20, avatarY + 34);
    ctx.fillStyle = "rgba(15,23,42,0.55)";
    ctx.font = "18px -apple-system, 'PingFang SC', sans-serif";
    ctx.fillText(`${p.value.date} · ${p.value.siteName}`, avatarX + avatarSize + 20, avatarY + 64);
    // 二维码
    const qrData = await QRCode.toDataURL(p.value.url, { width: 160, margin: 1, color: { dark: "#0f172a", light: "#ffffff" } });
    const qr = await new Promise<HTMLImageElement>((res) => {
      const img = new Image();
      img.onload = () => res(img);
      img.src = qrData;
    });
    const qx = p.value.width - 80 - 160;
    const qy = bottomY - 10;
    // 二维码白底
    ctx.fillStyle = "#fff";
    drawRoundedRect(ctx, qx - 8, qy - 8, 176, 176, 14);
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,0.06)";
    ctx.stroke();
    ctx.drawImage(qr, qx, qy, 160, 160);
    // 站点名在二维码下方
    ctx.fillStyle = "rgba(15,23,42,0.55)";
    ctx.font = "14px -apple-system, 'PingFang SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`长按识别 · ${p.value.siteName}`, qx + 80, qy + 160 + 24);
    ctx.textAlign = "start";
    generatedUrl.value = canvas.toDataURL("image/png");
  } catch (e) {
    console.warn("[SharePoster] generate failed:", e);
  } finally {
    generating.value = false;
  }
}

function download() {
  if (!generatedUrl.value) return;
  const a = document.createElement("a");
  a.href = generatedUrl.value;
  a.download = `poster-${dayjs().format("YYYYMMDD-HHmmss")}.png`;
  a.click();
}
</script>

<template>
  <div class="bg-neutral-bg-container rounded-2xl p-md shadow-sm border border-neutral-border-secondary">
    <div class="flex items-center justify-between mb-sm">
      <h3 class="text-sm font-semibold text-neutral-text-primary flex items-center gap-1.5">
        <Icon name="material-symbols:share-rounded" class="w-4 h-4 text-primary-500" />
        分享海报
      </h3>
      <button
        type="button"
        class="text-xs text-neutral-text-tertiary hover:text-primary-500 transition-colors"
        @click="open = !open"
      >
        {{ open ? '收起' : '展开' }}
      </button>
    </div>
    <Transition name="slide-down">
      <div v-show="open" class="space-y-sm">
        <div class="rounded-xl overflow-hidden border border-neutral-border-secondary bg-neutral-fill-hover max-w-[320px] mx-auto">
          <canvas
            ref="canvasEl"
            class="w-full h-auto block bg-white"
            :width="width"
            :height="height"
            aria-label="分享海报画布"
          />
          <div v-if="!generatedUrl && !generating" class="aspect-[2/3] flex flex-col items-center justify-center text-neutral-text-tertiary text-xs gap-sm">
            <Icon name="material-symbols:image-rounded" class="w-10 h-10 opacity-40" />
            <span>点击下方按钮生成分享海报</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400 disabled:opacity-60 transition-colors"
            :disabled="generating"
            @click="generate"
          >
            <Icon v-if="generating" name="material-symbols:progress-activity-rounded" class="w-4 h-4 animate-spin" />
            <Icon v-else name="material-symbols:auto-awesome-motion-rounded" class="w-4 h-4" />
            {{ generating ? '生成中…' : '生成海报' }}
          </button>
          <button
            type="button"
            class="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-neutral-border-secondary text-sm hover:bg-neutral-fill-hover transition-colors text-neutral-text-secondary disabled:opacity-50"
            :disabled="!generatedUrl"
            @click="download"
          >
            <Icon name="material-symbols:download-rounded" class="w-4 h-4" />
            下载
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.slide-down-enter-active, .slide-down-leave-active { transition: opacity 180ms ease, max-height 180ms ease; overflow: hidden; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; max-height: 0; }
.slide-down-enter-to, .slide-down-leave-from { opacity: 1; max-height: 1200px; }
</style>
