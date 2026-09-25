<template>
  <div class="rounded-xl border border-cortex-border bg-cortex-surface p-4 shadow-2xs" data-test="composer-stepper">
    <div class="flex items-center justify-between">
      <!-- Step 1 -->
      <div
        class="flex items-center gap-2 cursor-pointer"
        :class="{ 'opacity-60': currentStep < 1 }"
        @click="currentStep > 1 && emit('change-step', 1)"
      >
        <span
          class="flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs"
          :class="currentStep >= 1 ? 'bg-cortex-primary-600 text-white' : 'bg-cortex-surface-secondary text-cortex-text-muted'"
        >
          1
        </span>
        <span
          class="text-xs font-semibold"
          :class="currentStep === 1 ? 'text-cortex-primary-700 font-bold' : 'text-cortex-text-primary'"
        >
          {{ t('composer.step1_title') }}
        </span>
      </div>

      <div class="h-0.5 flex-1 bg-cortex-border mx-3" />

      <!-- Step 2 -->
      <div
        class="flex items-center gap-2 cursor-pointer"
        :class="{ 'opacity-60': currentStep < 2 }"
        @click="currentStep > 2 && emit('change-step', 2)"
      >
        <span
          class="flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs"
          :class="currentStep >= 2 ? 'bg-cortex-primary-600 text-white' : 'bg-cortex-surface-secondary text-cortex-text-muted'"
        >
          2
        </span>
        <span
          class="text-xs font-semibold"
          :class="currentStep === 2 ? 'text-cortex-primary-700 font-bold' : 'text-cortex-text-secondary'"
        >
          {{ t('composer.step2_title') }}
        </span>
      </div>

      <div class="h-0.5 flex-1 bg-cortex-border mx-3" />

      <!-- Step 3 -->
      <div
        class="flex items-center gap-2"
        :class="{ 'opacity-60': currentStep < 3 }"
      >
        <span
          class="flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs"
          :class="currentStep >= 3 ? 'bg-cortex-primary-600 text-white' : 'bg-cortex-surface-secondary text-cortex-text-muted'"
        >
          3
        </span>
        <span
          class="text-xs font-semibold"
          :class="currentStep === 3 ? 'text-cortex-primary-700 font-bold' : 'text-cortex-text-muted'"
        >
          {{ t('composer.step3_title') }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  currentStep: number
}>()

const emit = defineEmits<{
  (e: 'change-step', step: number): void
}>()
</script>
