<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-labelledby="damage-modal-title">
    <section class="w-full max-w-lg space-y-5 rounded-2xl border border-cortex-border bg-white p-6 shadow-2xl">
      <header class="flex items-start justify-between border-b pb-4"><div><h2 id="damage-modal-title" class="font-bold">Déclarer un dommage</h2><p class="mt-1 text-xs text-cortex-text-muted">{{ itemName }} · {{ serialNumber }}</p></div><button class="p-2" aria-label="Fermer" @click="close">✕</button></header>
      <fieldset class="grid grid-cols-3 gap-2 text-xs"><legend class="mb-2 font-semibold">Gravité</legend><label v-for="option in severities" :key="option.value" class="rounded-lg border p-3 text-center"><input v-model="severity" type="radio" :value="option.value" /> {{ option.label }}</label></fieldset>
      <label class="block text-xs font-semibold">Description du constat *<textarea v-model="description" rows="3" required class="mt-1 w-full rounded-xl border p-3 font-normal" /></label>
      <label class="block text-xs font-semibold">Photo de preuve (optionnelle)<input ref="fileInput" class="mt-2 block w-full text-xs" type="file" accept="image/*" capture="environment" @change="uploadEvidence" /></label>
      <p v-if="fileName" class="break-all rounded-lg bg-emerald-50 p-2 text-[11px] text-emerald-900">Fichier Frappe reçu : {{ fileName }}. Le hash sera créé côté serveur lors de la validation du check-in.</p>
      <p v-if="errorMessage" class="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">{{ errorMessage }}</p>
      <footer class="flex justify-end gap-2 border-t pt-3"><button class="cx-btn-secondary px-4 py-2 text-xs" @click="close">Annuler</button><button class="cx-btn-primary px-4 py-2 text-xs" :disabled="isSubmitting || !description.trim()" @click="submit">{{ isSubmitting ? 'Envoi…' : 'Ajouter au check-in' }}</button></footer>
    </section>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{ isOpen: boolean; rentalId: string; serialNumber: string; itemName: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'submitted', data: { serialNumber: string; severity: 'minor' | 'major' | 'unusable'; description: string; photoUploadId?: string }): void }>()
const severities = [{ value: 'minor', label: 'Mineur' }, { value: 'major', label: 'Majeur' }, { value: 'unusable', label: 'Inutilisable' }] as const
const severity = ref<'minor' | 'major' | 'unusable'>('major'); const description = ref(''); const fileName = ref(''); const isSubmitting = ref(false); const errorMessage = ref(''); const fileInput = ref<HTMLInputElement | null>(null)
async function uploadEvidence(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/') || file.size > 15 * 1024 * 1024) { errorMessage.value = 'Choisissez une image de 15 Mo maximum.'; return }
  isSubmitting.value = true; errorMessage.value = ''
  try {
    const form = new FormData(); form.append('file', file); form.append('is_private', '1'); form.append('doctype', 'Cortex Rental Transaction'); form.append('docname', props.rentalId)
    const csrf = (window as Window & { frappe?: { boot?: { csrf_token?: string } } }).frappe?.boot?.csrf_token
    const response = await fetch('/api/method/upload_file', { method: 'POST', credentials: 'include', headers: csrf ? { 'X-Frappe-CSRF-Token': csrf } : {}, body: form })
    const body = await response.json()
    const fileDoc = body.message
    if (!response.ok || !fileDoc?.name) throw new Error(body.exc_type || body.message || 'Frappe n’a pas reçu la photo.')
    fileName.value = fileDoc.name
  } catch (error) { errorMessage.value = error instanceof Error ? error.message : 'Échec du téléversement Frappe.' }
  finally { isSubmitting.value = false }
}
function close() { description.value = ''; fileName.value = ''; errorMessage.value = ''; if (fileInput.value) fileInput.value.value = ''; emit('close') }
function submit() { if (!description.value.trim()) return; emit('submitted', { serialNumber: props.serialNumber, severity: severity.value, description: description.value.trim(), ...(fileName.value ? { photoUploadId: fileName.value } : {}) }); close() }
</script>
