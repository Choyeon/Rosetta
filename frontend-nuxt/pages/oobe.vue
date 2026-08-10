<script setup lang="ts">
definePageMeta({ layout: "default", middleware: [] });
useHead({ title: "OOBE - Rosetta 首次配置向导" });

const step = ref(1);
const total = 5;
const env = reactive({ ok: false, node: "", python: "", db: "" });
const dbCfg = reactive({ type: "postgresql", host: "127.0.0.1", port: 5432, database: "rosetta", user: "postgres", password: "" });
const admin = reactive({ username: "admin", email: "", password: "", password2: "", nickname: "站长" });
const site = reactive({ title: "Rosetta", description: "以内容与体验为核心的现代化博客系统", url: "http://127.0.0.1:3000" });
const toggles = reactive({ comment: "twikoo", rss: true, sitemap: true, seo: true, search: true, analytics: false, cdnImage: false });

const loadingCheck = ref(false);
const submitting = ref(false);
const message = ref("");

async function envCheck() {
  loadingCheck.value = true; message.value = "";
  try {
    const r: any = await apiGet("/api/oobe/status");
    env.ok = true;
    env.node = process.versions.node;
    step.value = 2;
  } catch (e: any) { message.value = "无法连接后端。请确认 FastAPI 服务已启动（http://127.0.0.1:8000）。"; }
  finally { loadingCheck.value = false; }
}
async function submitAll() {
  submitting.value = true; message.value = "";
  try {
    const payload = { db: dbCfg, admin, site, features: toggles };
    const r: any = await apiPost("/api/oobe/init", payload);
    if (r?.accessToken || r?.data?.accessToken) {
      const auth = useAuthStore();
      auth.setAuth({ access_token: r.accessToken || r.data.accessToken, refresh_token: r.refreshToken || r.data.refreshToken });
    }
    step.value = 5;
    setTimeout(() => navigateTo("/admin", { replace: true }), 2000);
  } catch (e: any) { message.value = e?.message || "初始化失败"; }
  finally { submitting.value = false; }
}
</script>

<template>
  <div class="min-h-[85vh] flex items-center justify-center p-md">
    <div class="w-full max-w-3xl bg-neutral-bg-container rounded-2xl shadow-lg border border-neutral-border-secondary p-xl md:p-2xl space-y-xl">
      <!-- Progress -->
      <header class="space-y-md">
        <div class="flex items-center justify-between">
          <AppLogo size="md" />
          <span class="text-xs text-neutral-text-tertiary">步骤 {{ step }} / {{ total }}</span>
        </div>
        <div class="h-2 w-full rounded-full bg-neutral-fill-quaternary overflow-hidden">
          <div class="h-full bg-gradient-to-r from-primary-500 to-rosetta-gold transition-all" :style="{ width: `${(step/total)*100}%` }" />
        </div>
      </header>

      <!-- Step 1: Welcome -->
      <section v-if="step === 1" class="space-y-md">
        <h1 class="text-2xl font-bold text-neutral-text-primary">欢迎使用 Rosetta 🎉</h1>
        <p class="text-neutral-text-secondary leading-relaxed">
          我们将在 2 分钟内完成站点初始化：连接数据库、创建管理员、配置站点信息以及启用功能开关。<br/>
          若此前已完成初始化，你将被自动跳转到登录页。
        </p>
        <button
          @click="envCheck"
          :disabled="loadingCheck"
          class="h-11 px-6 rounded-lg bg-primary-500 text-white font-semibold hover:bg-primary-400 inline-flex items-center gap-xs disabled:opacity-60"
        >
          <Icon v-if="loadingCheck" name="eos-icons:loading" class="w-4 h-4 animate-spin" />
          {{ loadingCheck ? "检查环境…" : "开始 →" }}
        </button>
        <p v-if="message" class="text-sm text-danger-500">{{ message }}</p>
      </section>

      <!-- Step 2: Env -->
      <section v-else-if="step === 2" class="space-y-md">
        <h2 class="text-xl font-bold text-neutral-text-primary">数据库连接</h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-xs text-sm">
          <div><label class="text-xs text-neutral-text-secondary block mb-1">类型</label>
            <select v-model="dbCfg.type" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
            </select>
          </div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">Host</label><input v-model="dbCfg.host" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">Port</label><input v-model.number="dbCfg.port" type="number" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">数据库名</label><input v-model="dbCfg.database" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">用户</label><input v-model="dbCfg.user" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">密码</label><input v-model="dbCfg.password" type="password" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
        </div>
        <button @click="step = 3" class="h-10 px-5 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400">下一步 →</button>
      </section>

      <!-- Step 3: Admin -->
      <section v-else-if="step === 3" class="space-y-md">
        <h2 class="text-xl font-bold text-neutral-text-primary">管理员账号</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-xs text-sm">
          <div><label class="text-xs text-neutral-text-secondary block mb-1">用户名 *</label><input v-model="admin.username" required class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">昵称</label><input v-model="admin.nickname" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">邮箱</label><input v-model="admin.email" type="email" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">密码 *</label><input v-model="admin.password" type="password" required class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div><label class="text-xs text-neutral-text-secondary block mb-1">重复密码 *</label><input v-model="admin.password2" type="password" required class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
        </div>
        <button @click="step = 4" class="h-10 px-5 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-400">下一步 →</button>
      </section>

      <!-- Step 4: Site + Features -->
      <section v-else-if="step === 4" class="space-y-md">
        <h2 class="text-xl font-bold text-neutral-text-primary">站点信息 & 功能开关</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-xs text-sm">
          <div class="sm:col-span-2"><label class="text-xs text-neutral-text-secondary block mb-1">站点标题</label><input v-model="site.title" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
          <div class="sm:col-span-2"><label class="text-xs text-neutral-text-secondary block mb-1">站点描述</label><textarea rows="2" v-model="site.description" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"></textarea></div>
          <div class="sm:col-span-2"><label class="text-xs text-neutral-text-secondary block mb-1">站点 URL</label><input v-model="site.url" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-xs text-sm">
          <label class="flex items-center gap-xs p-xs"><input type="checkbox" v-model="toggles.rss" class="w-4 h-4 rounded border-neutral-border-secondary text-primary-500" />RSS / Atom</label>
          <label class="flex items-center gap-xs p-xs"><input type="checkbox" v-model="toggles.sitemap" class="w-4 h-4 rounded border-neutral-border-secondary text-primary-500" />Sitemap</label>
          <label class="flex items-center gap-xs p-xs"><input type="checkbox" v-model="toggles.seo" class="w-4 h-4 rounded border-neutral-border-secondary text-primary-500" />SEO 结构化</label>
          <label class="flex items-center gap-xs p-xs"><input type="checkbox" v-model="toggles.search" class="w-4 h-4 rounded border-neutral-border-secondary text-primary-500" />站内搜索</label>
          <label class="flex items-center gap-xs p-xs"><input type="checkbox" v-model="toggles.analytics" class="w-4 h-4 rounded border-neutral-border-secondary text-primary-500" />访问统计</label>
          <label class="flex items-center gap-xs p-xs"><input type="checkbox" v-model="toggles.cdnImage" class="w-4 h-4 rounded border-neutral-border-secondary text-primary-500" />图片 CDN</label>
        </div>
        <div class="flex items-center justify-between pt-xs">
          <button @click="step = 3" class="h-10 px-5 rounded-lg bg-neutral-fill-hover text-sm text-neutral-text-primary hover:bg-neutral-fill-active">← 上一步</button>
          <button @click="submitAll" :disabled="submitting" class="h-10 px-5 rounded-lg bg-rosetta-gold hover:bg-rosetta-gold-dark text-neutral-text-primary font-medium inline-flex items-center gap-xs disabled:opacity-60">
            <Icon v-if="submitting" name="eos-icons:loading" class="w-4 h-4 animate-spin"/>
            {{ submitting ? "提交中…" : "完成初始化 ✓" }}
          </button>
        </div>
        <p v-if="message" class="text-sm text-danger-500">{{ message }}</p>
      </section>

      <!-- Step 5: Done -->
      <section v-else class="py-lg text-center space-y-sm">
        <div class="w-20 h-20 rounded-full bg-success-500/15 text-success-500 inline-flex items-center justify-center">
          <Icon name="material-symbols:check-circle-rounded" class="w-10 h-10"/>
        </div>
        <h2 class="text-2xl font-bold text-neutral-text-primary">初始化完成！</h2>
        <p class="text-sm text-neutral-text-tertiary">正在为你跳转到管理后台…</p>
      </section>
    </div>
  </div>
</template>
