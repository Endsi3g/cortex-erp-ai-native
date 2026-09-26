<template>
  <!-- Claude-style input: rounded card, auto-growing textarea, clay send button. -->
  <form
    class="rounded-2xl border bg-white transition-shadow focus-within:border-[var(--cl-border-strong)]"
    :class="compact ? 'border-[var(--cl-border)] shadow-sm' : 'border-[var(--cl-border)] shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.035)] focus-within:shadow-[0_0.25rem_1.25rem_rgba(0,0,0,0.075)]'"
    @submit.prevent="submit"
  >
    <label :for="id" class="sr-only">{{ placeholder }}</label>
    <textarea
      :id="id"
      ref="input"
      v-model="draft"
      rows="1"
      :maxlength="4000"
      :disabled="disabled"
      :placeholder="placeholder"
      class="block max-h-[240px] w-full resize-none border-0 bg-transparent px-4 pt-3.5 text-[16px] leading-6 text-[var(--cl-text)] placeholder-[var(--cl-faint)] focus:ring-0"
      :class="compact ? 'min-h-[48px]' : 'min-h-[64px]'"
      @input="resize"
      @keydown.enter.exact.prevent="submit"
    />
    <div class="flex items-center justify-between gap-2 px-3 pb-3 pt-1">
      <div class="min-w-0 truncate text-xs text-[var(--cl-muted)]">
        <slot name="context" />
      </div>
      <button
        type="submit"
        class="flex size-8 shrink-0 items-center justify-center rounded-lg text-white transition-colors disabled:opacity-40"
        :class="draft.trim() && !disabled ? 'bg-[var(--cl-accent)] hover:bg-[var(--cl-accent-hover)]' : 'bg-[var(--cl-faint)]'"
        :disabled="!draft.trim() || disabled || busy"
        :aria-label="sendLabel"
      >
        <LoaderCircle v-if="busy" class="size-4 animate-spin" :stroke-width="2" aria-hidden="true" />
        <ArrowUp v-else class="size-4" :stroke-width="2.25" aria-hidden="true" />
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, useId } from 'vue'
import { ArrowUp, LoaderCircle } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  placeholder: string
  sendLabel: string
  disabled?: boolean
  busy?: boolean
  compact?: boolean
  autofocus?: boolean
}>(), { disabled: false, busy: false, compact: false, autofocus: false })

const emit = defineEmits<{ send: [text: string] }>()
const id = useId()
const draft = ref('')
const input = ref<HTMLTextAreaElement | null>(null)

function resize() {
  const el = input.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 240)}px`
}

function submit() {
  const text = draft.value.trim()
  if (!text || props.disabled || props.busy) return
  emit('send', text)
  draft.value = ''
  void nextTick(resize)
}

/** Put a suggestion in the box (the person still presses send). */
function fill(text: string) {
  draft.value = text
  void nextTick(() => {
    resize()
    input.value?.focus()
  })
}

defineExpose({ fill, focus: () => input.value?.focus() })

onMounted(() => {
  if (props.autofocus) input.value?.focus()
})
</script>
