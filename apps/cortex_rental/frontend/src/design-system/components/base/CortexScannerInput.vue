<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import CortexIcon from '../../icons/CortexIcon.vue';

interface Props {
  modelValue?: string;
  placeholder?: string;
  autoFocus?: boolean;
  disabled?: boolean;
  loading?: boolean;
  lastScanned?: string;
  feedbackStatus?: 'idle' | 'success' | 'warning' | 'error';
  statusMessage?: string;
  locale?: 'fr-CA' | 'en-CA';
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: 'Scanner ou saisir le numéro de série...',
  autoFocus: true,
  disabled: false,
  loading: false,
  lastScanned: undefined,
  feedbackStatus: 'idle',
  statusMessage: undefined,
  locale: 'fr-CA',
});

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void;
  (e: 'scan', payload: { raw: string; trimmed: string }): void;
  (e: 'clear'): void;
}>();

const inputRef = ref<HTMLInputElement | null>(null);
const localValue = ref(props.modelValue);

function focusInput() {
  nextTick(() => {
    if (inputRef.value && !props.disabled) {
      inputRef.value.focus({ preventScroll: true });
    }
  });
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault();
    const raw = localValue.value;
    const trimmed = raw.trim();
    if (trimmed.length > 0) {
      emit('scan', { raw, trimmed });
      localValue.value = '';
      emit('update:modelValue', '');
    }
    // Retain focus for fast-cadence warehouse scanning
    focusInput();
  }
}

function handleInput(e: Event) {
  const target = e.target as HTMLInputElement;
  localValue.value = target.value;
  emit('update:modelValue', target.value);
}

function handleClear() {
  localValue.value = '';
  emit('update:modelValue', '');
  emit('clear');
  focusInput();
}

onMounted(() => {
  if (props.autoFocus) {
    focusInput();
  }
});

defineExpose({
  focus: focusInput,
  clear: handleClear,
});
</script>

<template>
  <div
    :class="[
      'cx-scanner-container',
      `cx-scanner-container--${feedbackStatus}`,
      { 'cx-scanner-container--disabled': disabled, 'cx-scanner-container--loading': loading },
    ]"
  >
    <div class="cx-scanner-field">
      <!-- Scanner Icon -->
      <span class="cx-scanner-field__icon-prefix" aria-hidden="true">
        <CortexIcon name="barcode" :size="22" color="var(--cortex-text-muted, #436354)" />
      </span>

      <!-- 52px Monospace Input -->
      <input
        ref="inputRef"
        :value="localValue"
        type="text"
        autocomplete="off"
        autocorrect="off"
        autocapitalize="off"
        spellcheck="false"
        :placeholder="placeholder"
        :disabled="disabled || loading"
        class="cx-scanner-field__input"
        aria-label="Scanner de code-barres et numéro de série"
        @input="handleInput"
        @keydown="handleKeyDown"
      />

      <!-- Clear Button or Loading Indicator -->
      <div class="cx-scanner-field__actions">
        <span v-if="loading" class="cx-scanner-field__spinner" aria-hidden="true">
          <svg class="cx-scanner-field__spinner-svg" viewBox="0 0 24 24" fill="none">
            <circle class="cx-spinner-track" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
            <path class="cx-spinner-head" d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
          </svg>
        </span>
        <button
          v-else-if="localValue"
          type="button"
          class="cx-scanner-field__clear-btn"
          aria-label="Effacer le champ de scan"
          @click="handleClear"
        >
          <CortexIcon name="x" :size="16" />
        </button>
      </div>
    </div>

    <!-- Feedback Bar / Last Scanned Display -->
    <div v-if="statusMessage || lastScanned" class="cx-scanner-feedback" role="status" aria-live="polite">
      <div v-if="lastScanned" class="cx-scanner-feedback__last">
        <span class="cx-scanner-feedback__label">{{ locale === 'en-CA' ? 'Last scanned:' : 'Dernier scan :' }}</span>
        <code class="cx-scanner-feedback__serial">{{ lastScanned }}</code>
      </div>
      <div v-if="statusMessage" class="cx-scanner-feedback__msg">
        {{ statusMessage }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.cx-scanner-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  font-family: var(--font-sans, Inter, sans-serif);
}

.cx-scanner-field {
  position: relative;
  display: flex;
  align-items: center;
  height: 52px;
  background-color: var(--cortex-surface, #ffffff);
  border: 2px solid var(--cortex-border, #cbdcd2);
  border-radius: var(--radius-md, 8px);
  padding: 0 12px;
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(8, 18, 13, 0.04));
  transition: all var(--motion-fast, 120ms ease);
  box-sizing: border-box;
}

.cx-scanner-field:focus-within {
  border-color: var(--cortex-green-600, #087a43);
  box-shadow: 0 0 0 3px rgba(8, 122, 67, 0.15);
}

.cx-scanner-container--success .cx-scanner-field {
  border-color: var(--cortex-green-600, #087a43);
  background-color: var(--cortex-green-50, #edfbf2);
}

.cx-scanner-container--warning .cx-scanner-field {
  border-color: var(--cortex-warning-600, #d97706);
  background-color: var(--cortex-warning-50, #fffbeb);
}

.cx-scanner-container--error .cx-scanner-field {
  border-color: var(--cortex-danger-600, #dc2626);
  background-color: var(--cortex-danger-50, #fef2f2);
}

.cx-scanner-field__icon-prefix {
  display: flex;
  align-items: center;
  margin-right: 10px;
  flex-shrink: 0;
}

.cx-scanner-field__input {
  flex-grow: 1;
  height: 100%;
  border: none;
  background: transparent;
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 16px;
  font-weight: 600;
  color: var(--cortex-text, #08120d);
  letter-spacing: 0.02em;
  outline: none;
  padding: 0;
}

.cx-scanner-field__input::placeholder {
  font-family: var(--font-sans, Inter, sans-serif);
  font-size: 14px;
  font-weight: 400;
  color: var(--cortex-text-disabled, #6d9685);
}

.cx-scanner-field__actions {
  display: flex;
  align-items: center;
  margin-left: 8px;
}

.cx-scanner-field__clear-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: var(--cortex-text-muted, #436354);
  cursor: pointer;
}

.cx-scanner-field__clear-btn:hover {
  background-color: var(--cortex-surface-hover, #e3ece6);
  color: var(--cortex-text, #08120d);
}

.cx-scanner-field__spinner-svg {
  width: 18px;
  height: 18px;
  animation: cx-spin 0.8s linear infinite;
  color: var(--cortex-green-600, #087a43);
}

.cx-spinner-track {
  opacity: 0.2;
}

.cx-scanner-feedback {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 0 4px;
  gap: 8px;
}

.cx-scanner-feedback__last {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--cortex-text-muted, #436354);
}

.cx-scanner-feedback__serial {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-weight: 700;
  color: var(--cortex-text, #08120d);
  background-color: var(--cortex-surface-subtle, #f1f5f9);
  padding: 1px 6px;
  border-radius: 4px;
}

.cx-scanner-feedback__msg {
  font-weight: 600;
}

.cx-scanner-container--success .cx-scanner-feedback__msg {
  color: var(--cortex-green-800, #044727);
}

.cx-scanner-container--warning .cx-scanner-feedback__msg {
  color: var(--cortex-warning-800, #92400e);
}

.cx-scanner-container--error .cx-scanner-feedback__msg {
  color: var(--cortex-danger-700, #b91c1c);
}

@keyframes cx-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
