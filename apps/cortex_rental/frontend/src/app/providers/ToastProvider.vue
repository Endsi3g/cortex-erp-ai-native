<template>
  <slot />
  <!-- Global Toast Notification Outlet -->
  <div
    aria-live="polite"
    aria-atomic="true"
    class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
  >
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto flex items-start gap-2.5 p-3 rounded-xl border bg-cortex-surface shadow-lg text-xs font-medium"
        :class="getToastClass(toast.type)"
        role="alert"
      >
        <component :is="getToastIcon(toast.type)" class="w-4 h-4 flex-shrink-0 mt-0.5" />
        <div class="flex-1 min-w-0">
          <p class="font-semibold leading-tight text-cortex-text-primary">{{ toast.title }}</p>
          <p v-if="toast.message" class="text-[11px] text-cortex-text-secondary mt-0.5 leading-normal">
            {{ toast.message }}
          </p>
        </div>
        <button
          type="button"
          @click="removeToast(toast.id)"
          class="text-cortex-text-muted hover:text-cortex-text-primary p-0.5"
          aria-label="Fermer"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CheckCircle, AlertTriangle, AlertCircle, Info, X } from 'lucide-vue-next'

export interface ToastItem {
  id: string
  title: string
  message?: string
  type: 'success' | 'warning' | 'error' | 'info'
  duration?: number
}

const toasts = ref<ToastItem[]>([])

const removeToast = (id: string) => {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

const getToastClass = (type: ToastItem['type']) => {
  switch (type) {
    case 'success':
      return 'border-cortex-primary-400 bg-cortex-primary-50/80 text-cortex-primary-900'
    case 'warning':
      return 'border-amber-400 bg-amber-50/80 text-amber-900'
    case 'error':
      return 'border-red-400 bg-red-50/80 text-red-900'
    default:
      return 'border-cortex-border bg-cortex-surface text-cortex-text-primary'
  }
}

const getToastIcon = (type: ToastItem['type']) => {
  switch (type) {
    case 'success':
      return CheckCircle
    case 'warning':
      return AlertTriangle
    case 'error':
      return AlertCircle
    default:
      return Info
  }
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.95);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(24px);
}
</style>
