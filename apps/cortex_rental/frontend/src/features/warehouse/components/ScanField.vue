<template>
  <!-- 52px warehouse scan field: keeps focus between scans, Enter submits, audible + visual feedback. -->
  <form class="flex gap-2" @submit.prevent="submit">
    <label class="sr-only" :for="id">{{ label }}</label>
    <input
      :id="id"
      ref="input"
      v-model="value"
      type="text"
      inputmode="text"
      autocomplete="off"
      autocapitalize="characters"
      spellcheck="false"
      class="h-13 w-full rounded border-0 px-4 text-lg text-ink-gray-9 transition-colors focus:ring-2"
      :class="flash === 'ok' ? 'bg-surface-green-2 focus:ring-outline-green-2' : flash === 'error' ? 'bg-surface-red-2 focus:ring-outline-red-2' : 'bg-surface-gray-2 focus:ring-outline-gray-3'"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-describedby="`${id}-status`"
    />
    <Button type="submit" variant="solid" class="!h-13 px-5" :loading="busy" :disabled="disabled || !value.trim()">{{ submitLabel }}</Button>
    <p :id="`${id}-status`" class="sr-only" role="status" aria-live="assertive">{{ statusText }}</p>
  </form>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, useId } from 'vue'
import { Button } from 'frappe-ui'
import { ScannerFeedback, sanitizeBarcodeInput } from '@/utils/scanner'

const props = withDefaults(defineProps<{
  label: string
  placeholder: string
  submitLabel: string
  disabled?: boolean
  /** Returns an error message, or null when the scan was accepted. */
  onScan: (code: string) => Promise<string | null>
}>(), { disabled: false })

const id = useId()
const input = ref<HTMLInputElement | null>(null)
const value = ref('')
const busy = ref(false)
const flash = ref<'ok' | 'error' | null>(null)
const statusText = ref('')

async function submit() {
  const code = sanitizeBarcodeInput(value.value)
  if (!code || busy.value) return
  busy.value = true
  try {
    const error = await props.onScan(code)
    flash.value = error ? 'error' : 'ok'
    statusText.value = error ?? `${code} ✓`
    if (error) ScannerFeedback.playError()
    else {
      ScannerFeedback.playSuccess()
      value.value = ''
    }
  } finally {
    busy.value = false
    setTimeout(() => (flash.value = null), 600)
    await nextTick()
    input.value?.focus()
    if (flash.value === 'error') input.value?.select()
  }
}

onMounted(() => input.value?.focus())
defineExpose({ focus: () => input.value?.focus() })
</script>
