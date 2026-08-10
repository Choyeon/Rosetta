<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
const route = useRoute();
const id = computed(() => Number(route.params.id) || 0);
useHead({ title: computed(() => (id.value ? `编辑文章 #${id.value}` : "新建文章") + " - Rosetta 后台") });

const saving = ref(false);
const publishing = ref(false);

const form = reactive({
  title: "", slug: "", category: "", tags: "" as string | string[],
  description: "", image: "", content: "# 开始写作\n\n使用 **Markdown** 撰写内容。\n",
  status: "draft", pinned: false, lang: "zh",
  password: "", allowComment: true,
  metaTitle: "", metaDescription: "", metaKeywords: "",
  published: "",
});

// load
if (id.value) {
  const { data } = await useFetch<any>(() => `/api/admin/posts/${id.value}`, {
    lazy: true, server: false,
  });
  watch(data, (d) => {
    if (!d) return;
    const src = d.data || d;
    Object.assign(form, {
      title: src.title || "",
      slug: src.slug || "",
      category: src.category || "",
      tags: Array.isArray(src.tags) ? src.tags.join(", ") : (src.tags || ""),
      description: src.description || "",
      image: src.image || "",
      content: src.content || src.body || "",
      status: src.status || (src.published ? "published" : "draft"),
      pinned: !!src.pinned,
      lang: src.lang || "zh",
      password: src.password || "",
      allowComment: src.allowComment !== false,
      metaTitle: src.metaTitle || "",
      metaDescription: src.metaDescription || src.description || "",
      metaKeywords: (src.metaKeywords || (src.tags || []).join(", ")),
      published: src.published || "",
    });
  }, { immediate: true });
}

// categories/tags 参考
const { data: cats } = await useFetch<any[]>("/api/categories", { default: () => [], lazy: true, server: false });
const { data: tags } = await useFetch<any[]>("/api/tags", { default: () => [], lazy: true, server: false });

// Preview sync: auto slug from title
watch(() => form.title, (t) => { if (t && !form.slug) form.slug = String(t).toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, "-").replace(/^-|-$/g,"").slice(0, 120); });

async function save(publish: boolean) {
  const payload = {
    ...form,
    tags: typeof form.tags === "string" ? form.tags.split(/[,，]/).map(s => s.trim()).filter(Boolean) : (form.tags || []),
    status: publish ? "published" : (form.status || "draft"),
  };
  try {
    let r: any;
    if (id.value) r = await apiPut(`/api/admin/posts/${id.value}`, payload);
    else r = await apiPost("/api/admin/posts", payload);
    const createdId = id.value || r?.id || r?.data?.id;
    if (publish) { await navigateTo("/admin/posts?status=published"); }
    else { await navigateTo(`/admin/posts/${createdId}`); }
  } catch (e: any) { alert(e?.message || "保存失败"); }
  finally { saving.value = publishing.value = false; }
}

const preview = ref<"editor" | "split" | "preview">("split");
const body = computed(() => form.content || "");
</script>

<template>
  <div class="space-y-lg">
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-md">
      <div>
        <div class="text-xs text-neutral-text-tertiary">
          <NuxtLink to="/admin/posts" class="hover:text-primary-500">文章管理</NuxtLink> / {{ id ? `编辑 #${id}` : "新建" }}
        </div>
        <h1 class="text-2xl font-bold text-neutral-text-primary mt-xs">{{ id ? "编辑文章" : "新建文章" }}</h1>
      </div>
      <div class="flex items-center gap-xs flex-wrap">
        <NuxtLink
          v-if="id"
          target="_blank"
          :to="`/posts/${form.slug || id}`"
          class="px-4 h-10 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm inline-flex items-center gap-1"
        ><Icon name="material-symbols:open-in-new-rounded" class="w-4 h-4"/>查看</NuxtLink>
        <button :disabled="saving" @click="saving = true; save(false)" class="px-4 h-10 rounded-lg bg-neutral-fill-hover hover:bg-neutral-fill-active text-sm font-medium inline-flex items-center gap-1 disabled:opacity-60">
          <Icon v-if="saving" name="eos-icons:loading" class="w-4 h-4 animate-spin"/>
          <Icon v-else name="material-symbols:save-rounded" class="w-4 h-4"/>保存草稿
        </button>
        <button :disabled="publishing" @click="publishing = true; save(true)" class="px-5 h-10 rounded-lg bg-primary-500 text-white text-sm font-semibold hover:bg-primary-400 inline-flex items-center gap-1 shadow-sm disabled:opacity-60">
          <Icon v-if="publishing" name="eos-icons:loading" class="w-4 h-4 animate-spin"/>
          <Icon v-else name="material-symbols:rocket-launch-rounded" class="w-4 h-4"/>发布
        </button>
      </div>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-lg">
      <!-- Left: editor -->
      <div class="space-y-md min-w-0">
        <!-- Editor mode toggle + title -->
        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm p-md space-y-sm">
          <input v-model="form.title" type="text" placeholder="在这里输入标题（必填）" class="w-full text-2xl font-bold text-neutral-text-primary bg-transparent focus:outline-none placeholder:text-neutral-text-quaternary border-b border-dashed border-neutral-border-secondary pb-sm"/>
          <div class="flex items-center justify-between gap-xs flex-wrap">
            <div class="flex items-center gap-xs">
              <label class="text-xs text-neutral-text-tertiary">Slug</label>
              <input v-model="form.slug" class="h-8 w-64 px-3 rounded bg-neutral-bg-layout border border-neutral-border-secondary text-xs focus:outline-none focus:ring-2 focus:ring-primary-500/40" placeholder="auto-generated"/>
            </div>
            <div class="inline-flex items-center rounded-lg overflow-hidden border border-neutral-border-secondary text-xs">
              <button
                v-for="m in ([['editor','仅编辑'],['split','分屏'],['preview','仅预览']] as const)"
                :key="m[0]"
                @click="preview = m[0]"
                class="px-3 py-1.5 transition-all"
                :class="preview === m[0] ? 'bg-primary-500 text-white' : 'text-neutral-text-secondary hover:bg-neutral-fill-hover'"
              >{{ m[1] }}</button>
            </div>
          </div>
        </div>

        <!-- Editor / Preview -->
        <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm overflow-hidden">
          <div class="grid" :class="preview === 'editor' ? 'grid-cols-1' : preview === 'preview' ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'">
            <div v-show="preview !== 'preview'" class="border-b md:border-b-0 md:border-r border-neutral-border-secondary">
              <textarea v-model="form.content" spellcheck="false"
                class="w-full h-[60vh] p-md text-sm font-mono bg-neutral-bg-layout text-neutral-text-primary leading-6 resize-none focus:outline-none"
                placeholder="# 标题  ..."/>
            </div>
            <div v-show="preview !== 'editor'" class="h-[60vh] overflow-y-auto p-md prose prose-rosetta max-w-none text-sm bg-neutral-bg-container">
              <ContentRendererMarkdown value="{{ body }}" />
              <div class="text-xs text-neutral-text-tertiary pt-xs border-t border-neutral-border-secondary mt-xs">
                ⚠️ Markdown 预览使用 @nuxt/content MDC 渲染；最终前台效果请点击「查看」。
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Meta sidebar -->
      <aside class="space-y-md h-fit lg:sticky lg:top-20">
        <!-- Publication -->
        <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm p-md space-y-sm">
          <h3 class="text-sm font-semibold text-neutral-text-primary">发布</h3>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">状态</span>
            <select v-model="form.status" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm">
              <option value="draft">草稿</option>
              <option value="published">已发布</option>
              <option value="hidden">隐藏</option>
            </select>
          </label>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">发布时间</span>
            <input v-model="form.published" type="datetime-local" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm"/>
          </label>
          <label class="inline-flex items-center gap-xs text-xs cursor-pointer select-none">
            <input v-model="form.pinned" type="checkbox" class="w-4 h-4 text-primary-500 rounded"/> 置顶推荐
          </label>
          <label class="inline-flex items-center gap-xs text-xs cursor-pointer select-none">
            <input v-model="form.allowComment" type="checkbox" class="w-4 h-4 text-primary-500 rounded"/> 允许评论
          </label>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">语言</span>
            <select v-model="form.lang" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm">
              <option value="zh">简体中文</option>
              <option value="zh_Hant">繁体中文</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
            </select>
          </label>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">访问密码（空=公开）</span>
            <input v-model="form.password" type="text" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm"/>
          </label>
        </section>

        <!-- Taxonomy -->
        <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm p-md space-y-sm">
          <h3 class="text-sm font-semibold text-neutral-text-primary">分类 / 标签</h3>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">分类</span>
            <input v-model="form.category" list="cat-list" placeholder="新建或选择…" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm"/>
            <datalist id="cat-list"><option v-for="c in cats" :key="c.id||c.name" :value="c.name"/></datalist>
          </label>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">标签（逗号分隔）</span>
            <input v-model="form.tags" list="tag-list" placeholder="Nuxt, Vue, 迁移笔记…" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm"/>
            <datalist id="tag-list"><option v-for="t in tags" :key="t.id||t.name" :value="t.name"/></datalist>
          </label>
        </section>

        <!-- Thumbnail -->
        <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm p-md space-y-sm">
          <h3 class="text-sm font-semibold text-neutral-text-primary">封面</h3>
          <div class="aspect-video rounded-xl bg-neutral-fill-hover overflow-hidden relative flex items-center justify-center border border-dashed border-neutral-border-secondary group cursor-pointer"
               @click="window.dispatchEvent(new CustomEvent('open-media-picker', { detail: form }))">
            <NuxtImg v-if="form.image" :src="form.image" class="w-full h-full object-cover" format="avif" loading="lazy"/>
            <div v-else class="text-neutral-text-quaternary text-xs flex flex-col items-center gap-xs">
              <Icon name="material-symbols:add-photo-alternate-rounded" class="w-10 h-10"/>点击上传或粘贴 URL
            </div>
          </div>
          <input v-model="form.image" type="url" placeholder="https://…/cover.webp"
            class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-xs"/>
        </section>

        <!-- SEO -->
        <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl shadow-sm p-md space-y-sm">
          <h3 class="text-sm font-semibold text-neutral-text-primary">SEO</h3>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">Meta 标题</span>
            <input v-model="form.metaTitle" :placeholder="form.title" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm"/>
          </label>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">Meta 描述</span>
            <textarea v-model="form.metaDescription" rows="2" :placeholder="form.description" class="w-full p-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm resize-none"/>
          </label>
          <label class="block text-xs"><span class="text-neutral-text-tertiary mb-1 block">关键词</span>
            <input v-model="form.metaKeywords" placeholder="tag1, tag2, tag3" class="w-full h-9 px-2 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary text-sm"/>
          </label>
          <p class="text-[11px] text-neutral-text-quaternary pt-xs border-t border-neutral-border-secondary">
            留空则自动回退到文章标题 / 描述 / 标签。
          </p>
        </section>
      </aside>
    </div>
  </div>
</template>
