<template>
  <Dialog v-model="open" :options="{ title, size: 'md' }">
    <template #body-content>
      <p v-if="description" class="mb-3 text-p-base text-ink-gray-7">{{ description }}</p>
      <label class="block text-sm text-ink-gray-6" :for="id">{{ label }}</label>
      <textarea
        :id="id"
        v-model="reason"
        rows="3"
        class="mt-1.5 w-full rounded border-0 bg-surface-gray-2 px-2 py-1.5 text-base text-ink-gray-8 focus:ring-2 focus:ring-outline-gray-3"
        :aria-invalid="tooShort"
      />
      <p v-if="error" class="mt-2 text-p-sm text-ink-red-4" role="alert">{{ error }}</p>
    </template>
    <template #actions="{ close }">
      <div class="flex justify-end gap-2">
        <Button variant="subtle" :disabled="loading" @click="close">{{ cancelLabel }}</Button>
        <Button :theme="danger ? 'red' : 'gray'" variant="solid" :loading="loading" :disabled="tooShort" @click="$emit('confirm', reason.trim())">
          {{ confirmLabel }}
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  label: string
  confirmLabel: string
  cancelLabel: string
  description?: string
  danger?: boolean
  loading?: boolean
  error?: string
  minLength?: number
}>(), { description: '', danger: false, loading: false, error: '', minLength: 3 })

const emit = defineEmits<{ 'update:modelValue': [value: boolean]; confirm: [reason: string] }>()

const id = useId()
const reason = ref('')
const open = computed({ get: () => props.modelValue, set: value => emit('update:modelValue', value) })
const tooShort = computed(() => reason.value.trim().length < props.minLength)

watch(open, value => { if (value) reason.value = '' })
</script>
