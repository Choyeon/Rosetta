<script setup lang="ts">
definePageMeta({ layout: "default", middleware: [] });
useHead({ title: "登录 - Rosetta 后台" });
const auth = useAuthStore();
onMounted(() => { if (auth.isLogged) navigateTo("/admin", { replace: true }); });

const form = reactive({ username: "", password: "", remember: true });
const loading = ref(false);
const error = ref<string | null>(null);

async function onSubmit() {
  loading.value = true;
  error.value = null;
  try {
    const r: any = await apiPost("/api/auth/login", form);
    const at = r?.accessToken || r?.access_token || r?.data?.accessToken || r?.data?.access_token;
    const rt = r?.refreshToken || r?.refresh_token || r?.data?.refreshToken || r?.data?.refresh_token;
    if (!at) throw new Error(r?.message || "登录失败，未获取 token");
    // 取 me 资料
    let user: any = null;
    try { user = (await apiGet("/api/users/me"))?.data || (await apiGet("/api/users/me")); } catch { /* ignore */ }
    auth.setAuth({ access_token: at, refresh_token: rt, user });
    await navigateTo("/admin", { replace: true });
  } catch (e: any) {
    error.value = e?.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="min-h-[85vh] flex items-center justify-center p-md">
    <div class="w-full max-w-md bg-neutral-bg-container rounded-2xl shadow-lg border border-neutral-border-secondary p-xl md:p-2xl">
      <div class="flex flex-col items-center text-center mb-xl">
        <AppLogo size="lg" :clickable="false" />
        <h1 class="mt-lg text-2xl font-bold text-neutral-text-primary">欢迎回来</h1>
        <p class="mt-xs text-sm text-neutral-text-tertiary">登录 Rosetta 管理后台</p>
      </div>
      <form @submit.prevent="onSubmit" class="space-y-md">
        <div>
          <label class="text-xs font-medium text-neutral-text-secondary mb-1 block">用户名 / 邮箱</label>
          <input v-model="form.username" type="text" required autocomplete="username"
            class="w-full h-11 px-4 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all"
            placeholder="admin / choyu" />
        </div>
        <div>
          <label class="text-xs font-medium text-neutral-text-secondary mb-1 block">密码</label>
          <input v-model="form.password" type="password" required autocomplete="current-password"
            class="w-full h-11 px-4 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40 focus:border-primary-500 transition-all"
            placeholder="••••••••" />
        </div>
        <label class="inline-flex items-center gap-xs text-xs text-neutral-text-secondary cursor-pointer select-none">
          <input v-model="form.remember" type="checkbox" class="w-4 h-4 rounded border-neutral-border-secondary text-primary-500 focus:ring-primary-500" />
          记住登录（Cookie 保留 7 天）
        </label>
        <div v-if="error" class="text-sm text-danger-500 bg-danger-500/10 border border-danger-500/20 rounded-lg px-3 py-2">
          {{ error }}
        </div>
        <button
          :disabled="loading"
          type="submit"
          class="w-full h-11 rounded-lg bg-primary-500 text-white font-semibold shadow-sm hover:bg-primary-400 active:bg-primary-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center gap-xs"
        >
          <Icon v-if="loading" name="eos-icons:loading" class="w-4 h-4 animate-spin" />
          {{ loading ? "登录中…" : "登录" }}
        </button>
        <div class="text-center text-xs text-neutral-text-tertiary pt-xs">
          尚未初始化？<NuxtLink to="/oobe" class="text-primary-500 hover:underline">进入首次配置向导</NuxtLink>
        </div>
      </form>
    </div>
  </div>
</template>
