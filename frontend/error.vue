<template>
  <div class="error-page">
    <div class="error-card">
      <div class="error-code">
        {{ statusCode }}
      </div>
      <h1 class="error-title">
        {{ pageTitle }}
      </h1>
      <p class="error-desc">
        {{ pageDesc }}
      </p>
      <div class="error-actions">
        <button
          type="button"
          class="error-btn primary"
          @click="goHome"
        >
          {{ t('error.backHome') }}
        </button>
        <button
          v-if="statusCode >= 500"
          type="button"
          class="error-btn ghost"
          @click="reload"
        >
          {{ t('error.retry') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  error: {
    statusCode: number
    statusMessage?: string
    message?: string
  }
}>()

const { t } = useI18n()
const localePath = useLocalePath()

const statusCode = computed(() => props.error?.statusCode ?? 500)

const pageTitle = computed(() => {
  if (statusCode.value === 404) return t('error.notFoundTitle')
  return t('error.serverErrorTitle')
})

const pageDesc = computed(() => {
  if (statusCode.value === 404) return t('error.notFoundDesc')
  return props.error?.message || t('error.serverErrorDesc')
})

const goHome = () => {
  clearError({ redirect: localePath('/') })
}

const reload = () => {
  window.location.reload()
}

useHead({
  title: `${statusCode.value} · Rosetta`
})
</script>

<style scoped>
.error-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: var(--background, #f8fafc);
  color: var(--foreground, #0f172a);
}

.error-card {
  max-width: 28rem;
  width: 100%;
  text-align: center;
  padding: 3rem 2rem;
}

.error-code {
  font-size: clamp(5rem, 18vw, 8rem);
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  color: var(--primary, #0ea5e9);
  opacity: 0.9;
}

.error-title {
  margin-top: 1rem;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.error-desc {
  margin-top: 0.75rem;
  color: var(--muted-foreground, #64748b);
  font-size: 0.95rem;
  line-height: 1.6;
  word-break: break-word;
}

.error-actions {
  margin-top: 2rem;
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.error-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border-radius: 0.75rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s ease, background-color 0.15s ease;
  border: none;
}

.error-btn.primary {
  background: var(--primary, #0ea5e9);
  color: #fff;
}

.error-btn.primary:hover {
  filter: brightness(1.08);
}

.error-btn.ghost {
  background: var(--muted, #f1f5f9);
  color: var(--foreground, #0f172a);
}

.error-btn.ghost:hover {
  background: var(--muted-foreground, #e2e8f0);
}
</style>
