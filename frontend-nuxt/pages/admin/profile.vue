<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "个人资料 - Rosetta 后台" });
const auth = useAuthStore();
const me = reactive({ ...(auth.user || {}) });
watch(() => auth.user, (u) => u && Object.assign(me, u), { immediate: true });
const pwd = reactive({ old: "", n1: "", n2: "" });
const saving = ref(false);
const pwSaving = ref(false);
async function save() {
  saving.value = true;
  try { const r = await apiPut("/api/users/me", me); auth.user = r?.data || r; alert("已保存"); }
  catch (e: any) { alert(e?.message || "保存失败"); }
  finally { saving.value = false; }
}
async function changePwd() {
  if (pwd.n1 !== pwd.n2) { alert("两次输入的新密码不一致"); return; }
  if (!pwd.old || !pwd.n1) { alert("请填写完整"); return; }
  pwSaving.value = true;
  try { await apiPost("/api/users/me/password", { oldPassword: pwd.old, newPassword: pwd.n1 }); pwd.old = ""; pwd.n1 = ""; pwd.n2 = ""; alert("密码已更新"); }
  catch (e: any) { alert(e?.message || "更新失败"); }
  finally { pwSaving.value = false; }
}
function logout() { auth.logout(); navigateTo("/login", { replace: true }); }
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-lg max-w-6xl">
    <!-- Profile card -->
    <aside class="md:col-span-1 bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-xl shadow-sm text-center space-y-md">
      <div class="mx-auto w-24 h-24 rounded-2xl bg-gradient-to-br from-primary-500 via-nebula-blue to-rosetta-gold text-white flex items-center justify-center text-3xl font-bold shadow-lg">
        {{ (me.nickname || me.username || '?').slice(0,1).toUpperCase() }}
      </div>
      <div>
        <h2 class="font-bold text-neutral-text-primary">{{ me.nickname || me.username }}</h2>
        <p class="text-xs text-neutral-text-tertiary mt-xs">@{{ me.username }}</p>
        <div class="mt-xs flex flex-wrap items-center justify-center gap-xs">
          <span v-for="r in (me.roles||[])" :key="r"
            class="text-[10px] px-2 py-0.5 rounded font-medium"
            :class="r === 'super_admin' ? 'bg-danger-500/10 text-danger-500' : r === 'admin' ? 'bg-primary-500/10 text-primary-500' : r === 'editor' ? 'bg-info-500/10 text-info-500' : 'bg-neutral-fill-hover text-neutral-text-tertiary'">
            {{ r }}
          </span>
        </div>
      </div>
      <p class="text-xs text-neutral-text-quaternary">上次登录<br/>
        {{ me.lastLogin ? new Date(me.lastLogin).toLocaleString() : '—' }}
      </p>
      <button @click="logout" class="w-full h-10 rounded-lg bg-danger-500/10 text-danger-500 hover:bg-danger-500/20 text-sm font-medium inline-flex items-center justify-center gap-1 transition-colors">
        <Icon name="material-symbols:logout-rounded" class="w-4 h-4"/>退出登录
      </button>
    </aside>

    <!-- Edit -->
    <div class="md:col-span-2 space-y-md">
      <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
        <h2 class="font-semibold text-neutral-text-primary">基本资料</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <label><span class="text-xs text-neutral-text-tertiary mb-1 block">用户名（不可改）</span>
            <input :value="me.username" disabled class="w-full h-10 px-3 rounded-lg bg-neutral-fill-hover border border-neutral-border-secondary text-neutral-text-quaternary cursor-not-allowed"/></label>
          <label><span class="text-xs text-neutral-text-tertiary mb-1 block">昵称</span>
            <input v-model="me.nickname" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
          <label><span class="text-xs text-neutral-text-tertiary mb-1 block">邮箱</span>
            <input v-model="me.email" type="email" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
          <label><span class="text-xs text-neutral-text-tertiary mb-1 block">站点 / 主页</span>
            <input v-model="me.website" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
          <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">个人简介</span>
            <textarea v-model="me.bio" rows="3" class="w-full p-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40 resize-none"/></label>
          <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">GitHub / 社交</span>
            <div class="flex items-center gap-xs">
              <Icon name="mdi:github" class="w-4 h-4 text-neutral-text-tertiary"/>
              <input v-model="me.github" class="flex-1 h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/>
            </div>
          </label>
        </div>
        <div class="pt-sm border-t border-neutral-border-secondary flex justify-end">
          <button :disabled="saving" @click="save" class="px-5 h-10 rounded-lg bg-primary-500 text-white text-sm font-semibold hover:bg-primary-400 inline-flex items-center gap-1 disabled:opacity-60">
            <Icon v-if="saving" name="eos-icons:loading" class="w-4 h-4 animate-spin"/>
            <Icon v-else name="material-symbols:save-rounded" class="w-4 h-4"/>保存修改
          </button>
        </div>
      </section>

      <!-- Password -->
      <section class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-lg shadow-sm space-y-sm text-sm">
        <h2 class="font-semibold text-neutral-text-primary">修改密码</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-sm">
          <label class="sm:col-span-2"><span class="text-xs text-neutral-text-tertiary mb-1 block">当前密码</span>
            <input v-model="pwd.old" type="password" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
          <label><span class="text-xs text-neutral-text-tertiary mb-1 block">新密码</span>
            <input v-model="pwd.n1" type="password" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
          <label><span class="text-xs text-neutral-text-tertiary mb-1 block">确认新密码</span>
            <input v-model="pwd.n2" type="password" class="w-full h-10 px-3 rounded-lg bg-neutral-bg-layout border border-neutral-border-secondary focus:outline-none focus:ring-2 focus:ring-primary-500/40"/></label>
        </div>
        <div class="pt-sm border-t border-neutral-border-secondary flex justify-end">
          <button :disabled="pwSaving" @click="changePwd" class="px-5 h-10 rounded-lg bg-rosetta-gold hover:bg-rosetta-gold-dark text-neutral-text-primary text-sm font-semibold inline-flex items-center gap-1 disabled:opacity-60">
            <Icon v-if="pwSaving" name="eos-icons:loading" class="w-4 h-4 animate-spin"/>
            <Icon v-else name="material-symbols:key-rounded" class="w-4 h-4"/>更新密码
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
