<!--
  SakuraEffect — p5.js 樱花瓣粒子特效
  props: count (数量)、wind (水平风速 px/frame)、gravity (垂直重力)
  支持 data-sakura-enabled 属性或 runtimeConfig 判断启用
-->
<script setup lang="ts">
import type P5 from "p5";

interface Props {
  count?: number;
  wind?: number;
  gravity?: number;
  enabled?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  count: 24,
  wind: 0.8,
  gravity: 0.9,
  enabled: true,
});

const hostEl = ref<HTMLElement | null>(null);
let p5Instance: P5 | null = null;
let P5Ctor: typeof P5 | null = null;

onMounted(async () => {
  if (!props.enabled || !hostEl.value) return;
  try {
    const mod = await import("p5");
    P5Ctor = mod.default || (mod as any).P5 || (mod as any).default;
    if (!P5Ctor) return;
    const count = props.count;
    const wind = props.wind;
    const gravity = props.gravity;
    const sketch = (p: P5) => {
      const petals: any[] = [];
      const colors = ["#ffb7c5", "#ffc0cb", "#f8b4c4", "#f9d5e5", "#e8a5c0"];
      p.setup = () => {
        const c = p.createCanvas(p.windowWidth, p.windowHeight);
        c.parent(hostEl.value!);
        c.style("position", "fixed");
        c.style("top", "0");
        c.style("left", "0");
        c.style("pointer-events", "none");
        c.style("z-index", "1");
        p.pixelDensity(1);
        for (let i = 0; i < count; i++) {
          petals.push({
            x: p.random(p.width),
            y: p.random(p.height),
            r: p.random(6, 14),
            speed: p.random(0.6, 2.0),
            angle: p.random(p.TWO_PI),
            twinkle: p.random(0.02, 0.06),
            color: p.color(p.random(colors)),
          });
        }
      };
      p.windowResized = () => p.resizeCanvas(p.windowWidth, p.windowHeight);
      p.draw = () => {
        p.clear();
        for (const pt of petals) {
          p.push();
          p.translate(pt.x, pt.y);
          p.rotate(pt.angle);
          pt.angle += pt.twinkle;
          pt.x += wind + p.sin(pt.angle) * 0.4;
          pt.y += gravity + pt.speed;
          p.noStroke();
          p.fill(pt.color);
          p.beginShape();
          for (let a = 0; a < 5; a++) {
            const ang = (p.TWO_PI / 5) * a - p.HALF_PI;
            const sx = p.cos(ang) * pt.r;
            const sy = p.sin(ang) * pt.r * 0.65;
            p.vertex(sx, sy);
            const ang2 = ang + p.TWO_PI / 10;
            p.vertex(p.cos(ang2) * pt.r * 0.4, p.sin(ang2) * pt.r * 0.3);
          }
          p.endShape(p.CLOSE);
          p.pop();
          if (pt.y > p.height + 20) {
            pt.y = -20;
            pt.x = p.random(p.width);
          }
          if (pt.x > p.width + 20) pt.x = -20;
          if (pt.x < -20) pt.x = p.width + 20;
        }
      };
    };
    p5Instance = new (P5Ctor as any)(sketch);
  } catch (e) {
    console.warn("[SakuraEffect] init failed:", e);
  }
});

onBeforeUnmount(() => {
  try { p5Instance?.remove?.(); } catch { /* ignore */ }
  p5Instance = null;
});
</script>

<template>
  <ClientOnly>
    <div ref="hostEl" class="sakura-container pointer-events-none fixed inset-0 z-1 overflow-hidden" aria-hidden />
  </ClientOnly>
</template>
