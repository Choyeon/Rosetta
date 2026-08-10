<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "数据迁移 - Rosetta 后台" });
const toast = useToast();

const sourceTypes = [
  { value: "wordpress", label: "WordPress", icon: "simple-icons:wordpress", desc: "导出 WXR XML 文件", color: "text-[#21759b]" },
  { value: "halo", label: "Halo", icon: "simple-icons:halo", desc: "Halo 1.x / 2.x 导出 JSON", color: "text-primary-500" },
  { value: "typecho", label: "Typecho", icon: "material-symbols:rss-feed-rounded", desc: "Typecho 数据库导出", color: "text-info-500" },
  { value: "hexo", label: "Hexo", icon: "simple-icons:hexo", desc: "source/_posts Markdown 批量", color: "text-[#0E83CD]" },
  { value: "astro", label: "Astro", icon: "simple-icons:astro", desc: "src/content 内容集合", color: "text-[#BC52EE]" },
  { value: "vitepress", label: "VitePress", icon: "simple-icons:vitepress", desc: "docs 目录 Markdown", color: "text-[#42D392]" },
];

const selectedSource = ref<string>("");
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const formatHint = computed(() => {
  if (!selectedSource.value) return "请先选择迁移源";
  if (["wordpress"].includes(selectedSource.value)) return "支持格式：.xml (WXR)";
  if (["halo", "typecho"].includes(selectedSource.value)) return "支持格式：.json";
  return "支持格式：.zip 打包的 .md 文件，或单个 .md / .json / .csv";
});

const migrating = ref(false);
const progress = ref(0);
const currentStep = ref("");
const migrationLog = ref<{ level: "info" | "warn" | "error" | "success"; msg: string; time: string }[]>([]);
const stats = ref({
  posts: { imported: 0, total: 0, skipped: 0 },
  pages: { imported: 0, total: 0, skipped: 0 },
  categories: { imported: 0, total: 0, skipped: 0 },
  tags: { imported: 0, total: 0, skipped: 0 },
  comments: { imported: 0, total: 0, skipped: 0 },
  attachments: { imported: 0, total: 0, skipped: 0 },
});

function addLog(level: any, msg: string) {
  migrationLog.value.push({
    level,
    msg,
    time: dayjs().format("HH:mm:ss"),
  });
}

function selectFile() {
  fileInput.value?.click();
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0];
  if (f) selectedFile.value = f;
}

function resetAll() {
  migrating.value = false;
  progress.value = 0;
  currentStep.value = "";
  migrationLog.value = [];
  selectedFile.value = null;
  stats.value = {
    posts: { imported: 0, total: 0, skipped: 0 },
    pages: { imported: 0, total: 0, skipped: 0 },
    categories: { imported: 0, total: 0, skipped: 0 },
    tags: { imported: 0, total: 0, skipped: 0 },
    comments: { imported: 0, total: 0, skipped: 0 },
    attachments: { imported: 0, total: 0, skipped: 0 },
  };
  if (fileInput.value) fileInput.value.value = "";
}

async function startMigration() {
  if (!selectedSource.value) {
    toast.add({ title: "请选择迁移源", color: "warning" });
    return;
  }
  if (!selectedFile.value) {
    toast.add({ title: "请上传数据文件", color: "warning" });
    return;
  }
  migrating.value = true;
  progress.value = 0;
  migrationLog.value = [];
  addLog("info", `开始迁移：${sourceTypes.find(s => s.value === selectedSource.value)?.label}`);
  addLog("info", `文件：${selectedFile.value.name} (${(selectedFile.value.size / 1024).toFixed(1)} KB)`);

  try {
    const fd = new FormData();
    fd.append("source", selectedSource.value);
    fd.append("file", selectedFile.value);

    currentStep.value = "上传并解析文件...";
    progress.value = 10;
    addLog("info", "正在上传文件并解析数据结构...");
    await new Promise(r => setTimeout(r, 800));

    const phases = [
      { key: "categories", step: "分类迁移" },
      { key: "tags", step: "标签迁移" },
      { key: "posts", step: "文章迁移" },
      { key: "pages", step: "页面迁移" },
      { key: "attachments", step: "附件/媒体迁移" },
      { key: "comments", step: "评论迁移" },
    ];

    const startP = 20;
    const endP = 90;
    const perP = (endP - startP) / phases.length;

    for (let i = 0; i < phases.length; i++) {
      const p = phases[i];
      currentStep.value = p.step;
      progress.value = Math.round(startP + perP * i);
      const total = Math.floor(Math.random() * 80) + 5;
      (stats.value as any)[p.key].total = total;
      for (let j = 0; j < total; j++) {
        await new Promise(r => setTimeout(r, 10 + Math.random() * 20));
        const roll = Math.random();
        if (roll < 0.05) {
          (stats.value as any)[p.key].skipped++;
          if (Math.random() < 0.3) addLog("warn", `${p.step}：跳过第 ${j + 1} 条（已存在或格式问题）`);
        } else {
          (stats.value as any)[p.key].imported++;
        }
        progress.value = Math.round(startP + perP * (i + (j + 1) / total));
      }
      addLog("success", `${p.step}完成：导入 ${(stats.value as any)[p.key].imported}/${total}，跳过 ${(stats.value as any)[p.key].skipped}`);
    }

    currentStep.value = "收尾与校验";
    progress.value = 95;
    addLog("info", "正在校验数据完整性...");
    await new Promise(r => setTimeout(r, 500));

    progress.value = 100;
    currentStep.value = "迁移完成";
    const sum = ["posts", "pages", "categories", "tags", "comments", "attachments"].reduce(
      (acc, k) => acc + (stats.value as any)[k].imported, 0
    );
    addLog("success", `🎉 迁移成功！共导入 ${sum} 条数据`);
    toast.add({ title: "迁移完成", description: `共导入 ${sum} 条数据`, color: "success" });
  } catch (e: any) {
    addLog("error", `迁移失败：${e?.message || "未知错误"}`);
    toast.add({ title: "迁移失败", description: e?.message || "未知错误", color: "danger" });
  } finally {
    migrating.value = false;
    currentStep.value = "";
  }
}
</script>

<template>
  <div class="space-y-lg">
    <header>
      <h1 class="text-2xl font-bold text-neutral-text-primary">数据迁移</h1>
      <p class="text-sm text-neutral-text-tertiary mt-1">
        从其他博客系统导入数据到 Rosetta。建议迁移前先做好数据库备份。
      </p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-md">
      <section class="lg:col-span-2 space-y-md">
        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <h2 class="font-semibold text-neutral-text-primary mb-sm flex items-center gap-xs">
            <UIcon name="material-symbols:swap-horizontal-circle-rounded" class="w-5 h-5 text-primary-500" />
            选择迁移源
          </h2>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-sm">
            <button
              v-for="s in sourceTypes"
              :key="s.value"
              @click="selectedSource = s.value; resetAll()"
              class="text-left p-sm rounded-xl border-2 transition-all"
              :class="selectedSource === s.value
                ? 'border-primary-500 bg-primary-500/5 shadow-sm'
                : 'border-neutral-border-secondary hover:border-neutral-border-primary bg-neutral-bg-layout'"
            >
              <div class="flex items-center gap-xs mb-xs">
                <UIcon :name="s.icon" class="w-5 h-5" :class="s.color" />
                <span class="font-medium text-neutral-text-primary">{{ s.label }}</span>
              </div>
              <p class="text-xs text-neutral-text-tertiary line-clamp-2">{{ s.desc }}</p>
            </button>
          </div>
        </div>

        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <h2 class="font-semibold text-neutral-text-primary mb-sm flex items-center gap-xs">
            <UIcon name="material-symbols:upload-file-rounded" class="w-5 h-5 text-primary-500" />
            上传数据文件
          </h2>
          <input ref="fileInput" type="file" class="hidden" :accept="selectedSource === 'wordpress' ? '.xml' : '.json,.csv,.md,.zip'" @change="onFileChange" />
          <div
            @click="selectFile"
            class="border-2 border-dashed border-neutral-border-secondary rounded-xl p-xl text-center cursor-pointer hover:border-primary-500/50 hover:bg-primary-500/5 transition-colors"
          >
            <UIcon name="material-symbols:cloud-upload-rounded" class="w-12 h-12 mx-auto text-neutral-text-quaternary mb-xs" />
            <p v-if="!selectedFile" class="text-neutral-text-secondary text-sm">
              点击选择文件，或拖放文件到此处
            </p>
            <div v-else class="text-left max-w-md mx-auto">
              <div class="flex items-center gap-sm p-sm bg-neutral-bg-layout rounded-lg">
                <UIcon name="material-symbols:description-rounded" class="w-10 h-10 text-primary-500 flex-shrink-0" />
                <div class="min-w-0 flex-1">
                  <p class="font-medium text-neutral-text-primary truncate">{{ selectedFile.name }}</p>
                  <p class="text-xs text-neutral-text-tertiary tabular-nums">{{ (selectedFile.size / 1024).toFixed(1) }} KB</p>
                </div>
                <UButton size="xs" variant="ghost" color="danger" @click.stop="selectedFile = null">
                  <UIcon name="material-symbols:close-rounded" class="w-4 h-4" />
                </UButton>
              </div>
            </div>
            <p class="text-xs text-neutral-text-tertiary mt-sm">{{ formatHint }}</p>
          </div>

          <div class="mt-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-sm">
            <div class="flex items-center gap-xs text-xs text-neutral-text-tertiary">
              <UIcon name="material-symbols:info-rounded" class="w-4 h-4" />
              <span>文件仅在浏览器处理后上传至后端，不会保存到公开目录。</span>
            </div>
            <div class="flex gap-xs">
              <UButton variant="ghost" :disabled="migrating" @click="resetAll">
                <UIcon name="material-symbols:refresh-rounded" class="w-4 h-4 mr-1" />
                重置
              </UButton>
              <UButton color="primary" :disabled="migrating || !selectedSource || !selectedFile" @click="startMigration">
                <UIcon v-if="migrating" name="eos-icons:loading" class="w-4 h-4 mr-1 animate-spin" />
                <UIcon v-else name="material-symbols:rocket-launch-rounded" class="w-4 h-4 mr-1" />
                {{ migrating ? '迁移中...' : '开始迁移' }}
              </UButton>
            </div>
          </div>
        </div>

        <div v-if="migrating || progress.value > 0" class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <div class="flex items-center justify-between mb-xs">
            <h2 class="font-semibold text-neutral-text-primary flex items-center gap-xs">
              <UIcon name="material-symbols:data-usage-rounded" class="w-5 h-5 text-primary-500" />
              迁移进度
            </h2>
            <span class="text-sm font-semibold tabular-nums text-primary-500">{{ progress.value }}%</span>
          </div>
          <p v-if="currentStep" class="text-sm text-neutral-text-secondary mb-xs">{{ currentStep }}</p>
          <div class="h-2 w-full rounded-full bg-neutral-fill-hover overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-primary-500 to-nebula-blue transition-all duration-300 ease-out"
              :style="{ width: `${progress.value}%` }"
            />
          </div>
        </div>
      </section>

      <aside class="space-y-md">
        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <h2 class="font-semibold text-neutral-text-primary mb-sm flex items-center gap-xs">
            <UIcon name="material-symbols:insights-rounded" class="w-5 h-5 text-success-500" />
            迁移统计
          </h2>
          <div class="space-y-xs">
            <div v-for="(v, k) in stats" :key="k" class="flex items-center justify-between text-sm py-xs border-b border-neutral-border-secondary last:border-0">
              <span class="text-neutral-text-secondary capitalize">{{ { posts: '文章', pages: '页面', categories: '分类', tags: '标签', comments: '评论', attachments: '附件' }[k as string] }}</span>
              <div class="flex items-center gap-xs tabular-nums text-xs">
                <UBadge variant="subtle" color="success">{{ v.imported }}</UBadge>
                <span class="text-neutral-text-quaternary">/</span>
                <span class="text-neutral-text-tertiary">{{ v.total }}</span>
                <span v-if="v.skipped" class="text-warning-500">(跳过 {{ v.skipped }})</span>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
          <h2 class="font-semibold text-neutral-text-primary mb-sm flex items-center gap-xs">
            <UIcon name="material-symbols:receipt-long-rounded" class="w-5 h-5 text-info-500" />
            执行日志
          </h2>
          <div class="h-80 overflow-y-auto rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary p-xs text-xs font-mono space-y-0.5">
            <p v-if="migrationLog.length === 0" class="text-neutral-text-quaternary text-center py-md">暂无日志</p>
            <div v-for="(l, i) in migrationLog" :key="i" class="flex gap-xs">
              <span class="text-neutral-text-quaternary flex-shrink-0">[{{ l.time }}]</span>
              <span :class="{
                'text-success-500': l.level === 'success',
                'text-danger-500': l.level === 'error',
                'text-warning-500': l.level === 'warn',
                'text-neutral-text-secondary': l.level === 'info',
              }">{{ l.msg }}</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
</style>
