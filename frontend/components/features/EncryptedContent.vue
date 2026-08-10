<!--
  EncryptedContent — AES 加密内容解密渲染
  props: password（密码，可空=用输入框）、salt（AES 盐）
  slot: 默认 → 原文；通过 CryptoJS AES.encrypt(data, password+salt) 解密
  输入 UI：密码输入框 + 解密按钮；解密成功缓存 sessionStorage
-->
<script setup lang="ts">
import CryptoJS from "crypto-js";

interface Props {
  password?: string;
  salt?: string;
  hint?: string;
  storageKey?: string;
  dataEncrypted: string;
}
const props = withDefaults(defineProps<Props>(), {
  password: "",
  salt: "rosetta-salt",
  hint: "",
  storageKey: "",
  dataEncrypted: "",
});

const pwd = ref("");
const unlocked = ref(false);
const decrypted = ref<string>("");
const err = ref("");
const showInput = ref(!props.password);

function key(pw: string) { return `${pw}::${props.salt}`; }
const cacheKey = computed(() => props.storageKey || `rosetta-enc-${CryptoJS.MD5(props.dataEncrypted || props.salt).toString()}`);

function tryDecrypt(pw: string): string | null {
  if (!props.dataEncrypted || !pw) return null;
  try {
    const bytes = CryptoJS.AES.decrypt(props.dataEncrypted, key(pw));
    const s = bytes.toString(CryptoJS.enc.Utf8);
    if (!s) return null;
    return s;
  } catch {
    return null;
  }
}

function submit() {
  err.value = "";
  const pw = props.password || pwd.value;
  const r = tryDecrypt(pw);
  if (r === null) { err.value = "密码错误或密文损坏"; return; }
  decrypted.value = r;
  unlocked.value = true;
  try { sessionStorage.setItem(cacheKey.value, pw); } catch { /* ignore */ }
}

onMounted(() => {
  if (props.password) {
    const r = tryDecrypt(props.password);
    if (r !== null) { decrypted.value = r; unlocked.value = true; return; }
    showInput.value = true;
  }
  try {
    const saved = sessionStorage.getItem(cacheKey.value);
    if (saved) {
      const r = tryDecrypt(saved);
      if (r !== null) { decrypted.value = r; unlocked.value = true; showInput.value = false; pwd.value = saved; }
    }
  } catch { /* ignore */ }
});
</script>

<template>
  <section class="bg-neutral-bg-container rounded-xl border border-neutral-border-secondary p-md shadow-sm">
    <div v-if="!unlocked" class="space-y-sm">
      <div class="flex items-center gap-2 text-sm text-neutral-text-primary font-medium">
        <Icon name="material-symbols:lock-rounded" class="w-5 h-5 text-primary-500" />
        内容已加密
      </div>
      <p v-if="hint" class="text-xs text-neutral-text-tertiary">{{ hint }}</p>
      <form class="flex items-center gap-2" @submit.prevent="submit">
        <input
          v-model="pwd"
          type="password"
          :placeholder="showInput ? '请输入解密密码' : '已锁定，点击按钮解密'"
          class="flex-1 px-3 py-2 text-sm rounded-lg border border-neutral-border-secondary bg-neutral-bg-spot text-neutral-text-primary placeholder:text-neutral-text-quaternary focus:outline-none focus:ring-2 ring-primary-500/30 focus:border-primary-500 transition"
          :disabled="!showInput"
          @keyup.enter="submit"
        />
        <button
          type="submit"
          class="px-3 py-2 text-sm rounded-lg bg-primary-500 text-white hover:bg-primary-400 active:bg-primary-600 transition-colors duration-fast"
        >解密</button>
      </form>
      <p v-if="err" class="text-xs text-red-500">{{ err }}</p>
    </div>
    <div v-else class="decrypted-content">
      <slot :text="decrypted">{{ decrypted }}</slot>
    </div>
  </section>
</template>
