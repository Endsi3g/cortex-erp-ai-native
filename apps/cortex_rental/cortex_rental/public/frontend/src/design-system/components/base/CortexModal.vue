<script setup lang="ts">
import { ref, watch, onUnmounted, nextTick } from 'vue';
import CortexIcon from '../../icons/CortexIcon.vue';

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

interface Props {
  modelValue: boolean;
  title?: string;
  subtitle?: string;
  size?: ModalSize;
  preventClose?: boolean;
  showClose?: boolean;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  subtitle: undefined,
  size: 'md',
  preventClose: false,
  showClose: true,
  ariaLabel: undefined,
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'close'): void;
}>();

const modalContainerRef = ref<HTMLElement | null>(null);
const titleId = `cx-modal-title-${Math.random().toString(36).substring(2, 9)}`;

function close() {
  if (props.preventClose) return;
  emit('update:modelValue', false);
  emit('close');
}

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    close();
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (!props.modelValue) return;

  if (e.key === 'Escape') {
    e.preventDefault();
    close();
    return;
  }

  // Focus trap
  if (e.key === 'Tab' && modalContainerRef.value) {
    const focusable = modalContainerRef.value.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) return;

    const firstElement = focusable[0];
    const lastElement = focusable[focusable.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === firstElement) {
        lastElement.focus();
        e.preventDefault();
      }
    } else {
      if (document.activeElement === lastElement) {
        firstElement.focus();
        e.preventDefault();
      }
    }
  }
}

watch(
  () => props.modelValue,
  (isOpen) => {
    if (typeof document === 'undefined') return;
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
      nextTick(() => {
        if (modalContainerRef.value) {
          const firstFocusable = modalContainerRef.value.querySelector<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          if (firstFocusable) {
            firstFocusable.focus();
          } else {
            modalContainerRef.value.focus();
          }
        }
      });
    } else {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = '';
    window.removeEventListener('keydown', handleKeyDown);
  }
});
</script>

<template>
  <Teleport to="body">
    <Transition name="cx-modal-fade">
      <div
        v-if="modelValue"
        class="cx-modal-overlay"
        role="presentation"
        @click="handleBackdropClick"
      >
        <div
          ref="modalContainerRef"
          :class="['cx-modal-dialog', `cx-modal-dialog--${size}`]"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="title ? titleId : undefined"
          :aria-label="!title ? ariaLabel : undefined"
          tabindex="-1"
        >
          <!-- Header -->
          <header v-if="title || showClose || $slots.header" class="cx-modal-header">
            <slot name="header">
              <div class="cx-modal-heading">
                <h2 :id="titleId" class="cx-modal-title">{{ title }}</h2>
                <p v-if="subtitle" class="cx-modal-subtitle">{{ subtitle }}</p>
              </div>
            </slot>

            <button
              v-if="showClose"
              type="button"
              class="cx-modal-close-btn"
              aria-label="Fermer la fenêtre (Échap)"
              @click="close"
            >
              <CortexIcon name="x" :size="16" />
            </button>
          </header>

          <!-- Body -->
          <div class="cx-modal-body">
            <slot />
          </div>

          <!-- Footer -->
          <footer v-if="$slots.footer" class="cx-modal-footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.cx-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(4, 9, 6, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: var(--space-4, 16px);
  box-sizing: border-box;
}

.cx-modal-dialog {
  background-color: var(--cortex-surface, #ffffff);
  border: 1px solid var(--cortex-border, #cbdcd2);
  border-radius: var(--radius-lg, 12px);
  box-shadow: var(--shadow-lg, 0 12px 32px rgba(8, 18, 13, 0.12));
  font-family: var(--font-sans, Inter, sans-serif);
  color: var(--cortex-text, #08120d);
  max-height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  outline: none;
  width: 100%;
}

/* Sizes */
.cx-modal-dialog--sm {
  max-width: 400px;
}

.cx-modal-dialog--md {
  max-width: 540px;
}

.cx-modal-dialog--lg {
  max-width: 720px;
}

.cx-modal-dialog--xl {
  max-width: 900px;
}

.cx-modal-dialog--full {
  max-width: calc(100vw - 32px);
  height: calc(100vh - 32px);
}

.cx-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3, 12px);
  padding: var(--space-4, 16px) var(--space-5, 20px);
  border-bottom: 1px solid var(--cortex-border, #cbdcd2);
  flex-shrink: 0;
}

.cx-modal-heading {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cx-modal-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--cortex-text, #08120d);
}

.cx-modal-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--cortex-text-muted, #436354);
}

.cx-modal-close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm, 6px);
  background: transparent;
  border: none;
  color: var(--cortex-text-muted, #436354);
  cursor: pointer;
  transition: all var(--motion-fast, 120ms ease);
}

.cx-modal-close-btn:hover {
  background-color: var(--cortex-surface-hover, #e3ece6);
  color: var(--cortex-text, #08120d);
}

.cx-modal-close-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--cortex-surface, #ffffff), 0 0 0 4px var(--focus-ring-color, #087a43);
}

.cx-modal-body {
  padding: var(--space-5, 20px);
  overflow-y: auto;
  font-size: 13.5px;
  color: var(--cortex-text-secondary, #264034);
  line-height: 1.5;
  flex-grow: 1;
}

.cx-modal-footer {
  padding: var(--space-3, 12px) var(--space-5, 20px);
  border-top: 1px solid var(--cortex-border, #cbdcd2);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2, 8px);
  flex-shrink: 0;
}

/* Transitions */
.cx-modal-fade-enter-active,
.cx-modal-fade-leave-active {
  transition: opacity var(--motion-base, 180ms ease);
}

.cx-modal-fade-enter-from,
.cx-modal-fade-leave-to {
  opacity: 0;
}

.cx-modal-fade-enter-active .cx-modal-dialog,
.cx-modal-fade-leave-active .cx-modal-dialog {
  transition: transform var(--motion-base, 180ms ease);
}

.cx-modal-fade-enter-from .cx-modal-dialog,
.cx-modal-fade-leave-to .cx-modal-dialog {
  transform: scale(0.97) translateY(8px);
}
</style>
