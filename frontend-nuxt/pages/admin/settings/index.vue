<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "站点设置 - Rosetta 后台" });
const route = useRoute();
const tab = ref(String(route.query.tab || "basic"));

const basic = reactive({ title: "Rosetta", subtitle: "以内容与体验为核心的现代化博客系统", description: "", url: "http://127.0.0.1:3000",
  icp: "", copyright: `© ${new Date().getFullYear()} Rosetta`, keywords: "Rosetta,博客,个人站点", avatar: "", favicon: "", logo: "" });

const theme = reactive({ primary: "#1677ff", mode: "auto", accent: "nebula-blue", customCodeHead: "", customCodeBody: "",
  footer: "由 Rosetta 强力驱动" });

const seo = reactive({ openGraph: true, twitterCard: true, jsonLd: true, sitemapAuto: true, rssAuto: true,
  googleSiteVerification: "", bingSiteVerification: "",
  ogImage: "", ogImageTemplate: "gradient-title", robots: "index, follow" });

const features = reactive({ search: true, comment: "twikoo", analytics: "none", analyticsId: "",
  cdn: "none", cdnUrl: "", imageLazy: true, avifWebp: true,
  emailNotify: true, notifyEmail: "", commentAutoAudit: true,
  darkMode: true, i18n: true, langs: ["zh", "en", "ja", "zh_Hant"] });

const integrations = reactive({
  twikoo: { envId: "" },
  giscus: { repo: "", repoId: "", category: "", categoryId: "", mapping: "pathname" },
  waline: { serverUrl: "" },
  webhook: { url: "", secret: "", events: ["post.published", "comment.created"] },
  smtp: { host: "", port: 465, secure: true, user: "", pass: "", from: "" },
  objectStorage: { provider: "s3", endpoint: "", bucket: "", region: "", accessKey: "", secretKey: "", domain: "" },
});

// 载入
try {
  const r: any = await apiGet("/api/admin/settings");
  if (r?.basic) Object.assign(basic, r.basic);
  if (r?.theme) Object.assign(theme, r.theme);
  if (r?.seo) Object.assign(seo, r.seo);
  if (r?.features) Object.assign(features, r.features);
  if (r?.integrations) Object.assign(integrations, r.integrations);
} catch { /* 使用默认值 */ }

const saving = ref(false);
async function save() {
  saving.value = true;
  try {
    await apiPost("/api/admin/settings", { basic, theme, seo, features, integrations });
    alert("保存成功");
  } catch (e: any) { alert(e?.message || "保存失败"); }
  finally { saving.value = false; }
}

const tabs = [
  ["basic", "基础", "material-symbols:home-rounded"],
  ["theme", "外观", "material-symbols:palette-rounded"],
  ["seo", "SEO", "material-symbols:travel-explore-rounded"],
  ["features", "功能", "material-symbols:tune-rounded"],
  ["integrations", "集成", "material-symbols:settings-suggest-rounded"],
] as const;
</script>

<template>
  <div class="space-y-lg">
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-md">
      <div>
        <div class="text-xs text-neutral-text-tertiary">
          <NuxtLink to="/admin" class="hover:text-primary-500">控制台</NuxtLink> / 站点设置
        </div>
        <h1 class="text-2xl font-bold text-neutral-text-primary mt-xs">站点设置</h1>
      </div>
      <button :disabled="saving" @click="save" class="px-5 h-10 rounded-lg bg-primary-500 text-white text-sm font-semibold hover:bg-primary-400 inline-flex items-center gap-1 shadow-sm disabled:opacity-60">
        <Icon v-if="saving" name="eos-icons:loading" class="w-4 h-4 animate-spin"/>
        <Icon v-else name="material-symbols:save-rounded" class="w-4 h-4"/>保存全部
      </button>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-lg">
      <!-- Tabs -->
      <nav class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-xs h-fit lg:sticky lg:top-20 space-y-0.5">
        <button v-for="[k,l,i] in tabs" :key="k"
          @click="tab = k; navigateTo({ path: '/admin/settings', query: { tab: k } }, { replace: true })"
          class="w-full px-3 h-10 rounded-lg flex items-center gap-xs text-sm transition-all"
          :class="tab === k ? 'bg-primary-500 text-white shadow-sm' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover'"
        >
          <Icon :name="i" class="w-4 h-4"/> {{ l }}
        </button>
      </nav>

      <!-- Panels -->
      <div class="space-y-md">
        <!-- 基础 -->
        <section v-show="tab === 'basic'" class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-md text-sm">
          <h2 class="font-semibold text-neutral-text-primary">基础配置</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">站点标题 *</span>
              <input v-model="basic.title" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">副标题</span>
              <input v-model="basic.subtitle" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">站点描述 (SEO)</span>
              <textarea v-model="basic.description" rows="2" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">站点 URL</span>
              <input v-model="basic.url" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">关键词（, 分隔）</span>
              <input v-model="basic.keywords" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Logo URL</span>
              <input v-model="basic.logo" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">头像 URL</span>
              <input v-model="basic.avatar" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">Favicon URL</span>
              <input v-model="basic.favicon" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">ICP 备案号</span>
              <input v-model="basic.icp" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">版权 / Footer 文案</span>
              <input v-model="basic.copyright" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
          </div>
        </section>

        <!-- 外观 -->
        <section v-show="tab === 'theme'" class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-md text-sm">
          <h2 class="font-semibold text-neutral-text-primary">外观 & 主题</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">主色</span>
              <div class="flex items-center gap-xs">
                <input v-model="theme.primary" type="color" class="h-10 w-14 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/>
                <input v-model="theme.primary" class="flex-1 h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/>
              </div>
            </label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">默认配色</span>
              <select v-model="theme.mode" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                <option value="auto">跟随系统</option>
                <option value="light">浅色</option>
                <option value="dark">深色</option>
              </select>
            </label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">副色（Accent）</span>
              <div class="flex items-center gap-xs flex-wrap">
                <button v-for="(c,n) in ({ 'nebula-blue':'星云蓝','rosetta-gold':'流沙金','rose':'玫瑰','mint':'薄荷','lavender':'薰衣草' } as Record<string,string>)"
                  :key="c"
                  @click="theme.accent = c"
                  class="px-3 py-1 rounded-full text-xs border transition-all"
                  :class="theme.accent === c ? 'bg-primary-500 text-white border-primary-500' : 'border-neutral-border-secondary text-neutral-text-secondary hover:border-primary-500/40'"
                >{{ n }}</button>
              </div>
            </label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">自定义 Footer HTML</span>
              <textarea v-model="theme.footer" rows="2" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs resize-none"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">自定义 &lt;head&gt; 代码（注入全站）</span>
              <textarea v-model="theme.customCodeHead" rows="4" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs resize-none" placeholder="<script async src='...'></script>"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">自定义 &lt;body&gt; 尾部代码（统计 / Live Chat）</span>
              <textarea v-model="theme.customCodeBody" rows="4" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs resize-none"/></label>
          </div>
        </section>

        <!-- SEO -->
        <section v-show="tab === 'seo'" class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-md text-sm">
          <h2 class="font-semibold text-neutral-text-primary">SEO & 搜索</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
            <label v-for="(k,i) in [['openGraph','Open Graph (Facebook/微信分享)'],['twitterCard','Twitter Card'],['jsonLd','JSON-LD 结构化'],['sitemapAuto','自动生成 Sitemap'],['rssAuto','自动生成 RSS / Atom'],['imageLazy','图片懒加载'],['avifWebp','自动 AVIF/WebP']]" :key="k"
              class="flex items-center gap-xs p-xs rounded-lg hover:bg-neutral-fill-hover cursor-pointer select-none">
              <input v-model="(seo as any)[k]" type="checkbox" class="w-4 h-4 text-primary-500 rounded"/>
              <div>
                <p class="text-sm font-medium text-neutral-text-primary">{{ i.split('（')[0] }}</p>
                <p v-if="i.includes('（')" class="text-xs text-neutral-text-quaternary">{{ i.slice(i.indexOf('（')+1, -1) }}</p>
              </div>
            </label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">默认分享缩略图 (og:image)</span>
              <input v-model="seo.ogImage" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">og:image 模板</span>
              <select v-model="seo.ogImageTemplate" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                <option value="gradient-title">渐变标题</option>
                <option value="cover">使用文章封面</option>
                <option value="custom">自定义图片</option>
              </select>
            </label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Google site verification</span>
              <input v-model="seo.googleSiteVerification" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Bing site verification</span>
              <input v-model="seo.bingSiteVerification" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">robots meta</span>
              <input v-model="seo.robots" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
          </div>
        </section>

        <!-- 功能 -->
        <section v-show="tab === 'features'" class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-md text-sm">
          <h2 class="font-semibold text-neutral-text-primary">功能开关</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">评论系统</span>
              <select v-model="features.comment" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                <option value="none">关闭</option>
                <option value="twikoo">Twikoo</option>
                <option value="giscus">Giscus</option>
                <option value="waline">Waline</option>
                <option value="disqus">Disqus</option>
              </select>
            </label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">站内搜索</span>
              <select v-model="features.search ? 'local' : 'off'" @change="(e: any) => features.search = (e.target.value === 'local')" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                <option value="local">本地索引 + /api/posts 回退</option>
                <option value="off">关闭</option>
              </select>
            </label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">访问统计</span>
              <select v-model="features.analytics" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                <option value="none">无</option>
                <option value="ga4">Google Analytics 4</option>
                <option value="umami">Umami</option>
                <option value="plausible">Plausible</option>
                <option value="baidu">百度统计</option>
              </select>
            </label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">统计 ID / 脚本 URL</span>
              <input v-model="features.analyticsId" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">图片 CDN</span>
              <select v-model="features.cdn" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                <option value="none">无</option><option value="jsdelivr">jsDelivr</option><option value="cloudflare">Cloudflare Images</option><option value="custom">自定义</option>
              </select>
            </label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">CDN 前缀</span>
              <input v-model="features.cdnUrl" placeholder="https://img.example.com/" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">通知收件邮箱</span>
              <input v-model="features.notifyEmail" type="email" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            <label class="inline-flex items-center gap-xs cursor-pointer p-xs select-none">
              <input v-model="features.emailNotify" type="checkbox" class="w-4 h-4 text-primary-500"/>新评论 / 新注册邮件通知
            </label>
            <label class="inline-flex items-center gap-xs cursor-pointer p-xs select-none">
              <input v-model="features.commentAutoAudit" type="checkbox" class="w-4 h-4 text-primary-500"/>评论需审核
            </label>
            <label class="inline-flex items-center gap-xs cursor-pointer p-xs select-none">
              <input v-model="features.darkMode" type="checkbox" class="w-4 h-4 text-primary-500"/>启用深色模式切换
            </label>
            <label class="inline-flex items-center gap-xs cursor-pointer p-xs select-none">
              <input v-model="features.i18n" type="checkbox" class="w-4 h-4 text-primary-500"/>启用多语言
            </label>
            <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">启用语言（, 分隔，默认 zh/en/ja/zh_Hant）</span>
              <input :value="features.langs.join(', ')" @input="features.langs = ($event.target as HTMLInputElement).value.split(/[,，]/).map(s=>s.trim()).filter(Boolean)"
                class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
          </div>
        </section>

        <!-- 集成 -->
        <section v-show="tab === 'integrations'" class="space-y-md">
          <!-- Twikoo -->
          <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
            <h3 class="font-semibold text-neutral-text-primary inline-flex items-center gap-xs">
              <Icon name="mdi:wechat" class="w-5 h-5 text-success-500"/>Twikoo 评论
            </h3>
            <p class="text-xs text-neutral-text-tertiary -mt-xs">腾讯云 CloudBase / Vercel 部署。环境 ID 或完整服务器地址。</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
              <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">Env ID / ServerURL</span>
                <input v-model="integrations.twikoo.envId" placeholder="https://twikoo.example.com" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            </div>
          </div>

          <!-- Giscus -->
          <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
            <h3 class="font-semibold text-neutral-text-primary inline-flex items-center gap-xs">
              <Icon name="mdi:github" class="w-5 h-5"/>Giscus（GitHub Discussions）
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Repo</span><input v-model="integrations.giscus.repo" placeholder="user/repo" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Repo ID</span><input v-model="integrations.giscus.repoId" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Category</span><input v-model="integrations.giscus.category" placeholder="General" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Category ID</span><input v-model="integrations.giscus.categoryId" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
              <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">映射</span>
                <select v-model="integrations.giscus.mapping" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                  <option value="pathname">pathname</option>
                  <option value="url">url</option>
                  <option value="title">title</option>
                  <option value="og:title">og:title</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Waline -->
          <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
            <h3 class="font-semibold text-neutral-text-primary">Waline</h3>
            <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Server URL</span>
              <input v-model="integrations.waline.serverUrl" placeholder="https://waline.example.com" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
          </div>

          <!-- Webhook -->
          <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
            <h3 class="font-semibold text-neutral-text-primary">Webhook 事件</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
              <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">URL</span>
                <input v-model="integrations.webhook.url" placeholder="https://hooks.example.com/xx" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
              <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">Secret</span>
                <input v-model="integrations.webhook.secret" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
              <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">事件（, 分隔）</span>
                <input :value="integrations.webhook.events.join(', ')" @input="integrations.webhook.events = ($event.target as HTMLInputElement).value.split(/[,，]/).map(s=>s.trim()).filter(Boolean)"
                  placeholder="post.published, comment.created, user.registered" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
            </div>
          </div>

          <!-- SMTP -->
          <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
            <h3 class="font-semibold text-neutral-text-primary">SMTP 邮件</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Host</span><input v-model="integrations.smtp.host" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Port</span><input v-model.number="integrations.smtp.port" type="number" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label class="inline-flex items-center gap-xs self-center cursor-pointer select-none"><input v-model="integrations.smtp.secure" type="checkbox" class="w-4 h-4 text-primary-500"/>SSL / SMTPS</label>
              <label></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">用户</span><input v-model="integrations.smtp.user" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">密码</span><input v-model="integrations.smtp.pass" type="password" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">发件人</span>
                <input v-model="integrations.smtp.from" placeholder="Rosetta <noreply@example.com>" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            </div>
          </div>

          <!-- 对象存储 -->
          <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
            <h3 class="font-semibold text-neutral-text-primary">对象存储（媒体上传）</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Provider</span>
                <select v-model="integrations.objectStorage.provider" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary">
                  <option value="s3">S3 兼容</option><option value="oss">阿里云 OSS</option><option value="cos">腾讯云 COS</option><option value="qiniu">七牛云 Kodo</option><option value="r2">Cloudflare R2</option><option value="local">本地磁盘</option>
                </select>
              </label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Endpoint</span><input v-model="integrations.objectStorage.endpoint" placeholder="https://s3.aws.com" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Region</span><input v-model="integrations.objectStorage.region" placeholder="us-east-1" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Bucket</span><input v-model="integrations.objectStorage.bucket" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Access Key</span><input v-model="integrations.objectStorage.accessKey" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
              <label><span class="text-xs text-neutral-text-tertiary mb-1 block">Secret Key</span><input v-model="integrations.objectStorage.secretKey" type="password" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary font-mono text-xs"/></label>
              <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">自定义域名</span>
                <input v-model="integrations.objectStorage.domain" placeholder="https://img.example.com" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary"/></label>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
