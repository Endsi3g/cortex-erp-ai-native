<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto"
    role="dialog"
    aria-modal="true"
    aria-labelledby="damage-modal-title"
  >
    <div
      class="bg-cortex-surface border border-cortex-border rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150"
    >
      <!-- Modal Header -->
      <div class="flex items-start justify-between border-b border-cortex-border pb-4">
        <div>
          <div class="flex items-center gap-2">
            <span class="p-1.5 rounded-lg bg-red-100 text-red-700">
              <AlertTriangle class="w-5 h-5" />
            </span>
            <h3 id="damage-modal-title" class="text-base font-bold text-cortex-text-primary">
              {{ $t('checkin.damage_evidence_title', 'Déclarer un Dommage / Casse') }}
            </h3>
          </div>
          <p class="text-xs text-cortex-text-muted mt-1">
            {{ itemName }} — <span class="font-mono font-semibold text-cortex-text-primary">{{ serialNumber }}</span>
          </p>
        </div>
        <button
          class="p-2 text-cortex-text-muted hover:text-cortex-text-primary rounded-lg hover:bg-cortex-surface-muted transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Fermer"
          @click="handleClose"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Severity Selection -->
      <div class="space-y-2">
        <label class="block text-xs font-bold uppercase tracking-wider text-cortex-text-muted">
          {{ $t('checkin.severity_label', 'Gravité du dommage') }}
        </label>
        <div class="grid grid-cols-3 gap-2">
          <button
            type="button"
            class="p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition-all min-h-[44px]"
            :class="
              severity === 'minor'
                ? 'border-amber-500 bg-amber-50 text-amber-900 ring-2 ring-amber-500/20'
                : 'border-cortex-border bg-cortex-surface text-cortex-text-secondary hover:bg-cortex-surface-muted'
            "
            @click="severity = 'minor'"
          >
            <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span>{{ $t('checkin.severity_minor', 'Mineur') }}</span>
            <span class="text-[10px] text-cortex-text-muted font-normal">Cosmétique</span>
          </button>

          <button
            type="button"
            class="p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition-all min-h-[44px]"
            :class="
              severity === 'major'
                ? 'border-orange-500 bg-orange-50 text-orange-900 ring-2 ring-orange-500/20'
                : 'border-cortex-border bg-cortex-surface text-cortex-text-secondary hover:bg-cortex-surface-muted'
            "
            @click="severity = 'major'"
          >
            <span class="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
            <span>{{ $t('checkin.severity_major', 'Majeur') }}</span>
            <span class="text-[10px] text-cortex-text-muted font-normal">Réparation</span>
          </button>

          <button
            type="button"
            class="p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition-all min-h-[44px]"
            :class="
              severity === 'unusable'
                ? 'border-red-600 bg-red-50 text-red-900 ring-2 ring-red-600/20'
                : 'border-cortex-border bg-cortex-surface text-cortex-text-secondary hover:bg-cortex-surface-muted'
            "
            @click="severity = 'unusable'"
          >
            <span class="w-2.5 h-2.5 rounded-full bg-red-600"></span>
            <span>{{ $t('checkin.severity_unusable', 'Inutilisable') }}</span>
            <span class="text-[10px] text-red-600 font-semibold">Quarantaine</span>
          </button>
        </div>
      </div>

      <!-- Description Input -->
      <div class="space-y-2">
        <label for="damage-description" class="block text-xs font-bold uppercase tracking-wider text-cortex-text-muted">
          {{ $t('checkin.description_label', 'Description du constat') }} *
        </label>
        <textarea
          id="damage-description"
          v-model="description"
          rows="3"
          class="w-full px-3 py-2.5 rounded-xl border border-cortex-border bg-cortex-surface-muted text-sm text-cortex-text-primary focus:outline-none focus:ring-2 focus:ring-red-500/30 focus:border-red-500 transition-colors"
          :placeholder="$t('checkin.description_placeholder', 'Décrire précisément le dommage, la rayure, le choc ou le dysfonctionnement...')"
        ></textarea>
      </div>

      <!-- Photo Upload Evidence -->
      <div class="space-y-2">
        <label class="block text-xs font-bold uppercase tracking-wider text-cortex-text-muted">
          {{ $t('checkin.photo_evidence_label', 'Preuve photo / constat SHA-256') }}
        </label>

        <div v-if="!photoUploaded" class="border-2 border-dashed border-cortex-border rounded-xl p-4 text-center space-y-2 bg-cortex-surface-muted/50">
          <Camera class="w-8 h-8 mx-auto text-cortex-text-muted" />
          <p class="text-xs text-cortex-text-secondary">
            {{ $t('checkin.upload_prompt', 'Prendre une photo ou importer un cliché haute-résolution') }}
          </p>
          <button
            type="button"
            class="px-4 py-2 bg-cortex-surface border border-cortex-border hover:bg-cortex-surface-muted text-xs font-semibold rounded-lg shadow-sm transition-colors min-h-[44px]"
            @click="simulatePhotoUpload"
          >
            📸 {{ $t('checkin.simulate_photo_btn', 'Simuler capture photo') }}
          </button>
        </div>

        <!-- Uploaded Evidence Badge -->
        <div v-else class="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1.5">
          <div class="flex items-center justify-between text-xs text-emerald-900 font-semibold">
            <span class="flex items-center gap-1.5">
              <CheckCircle class="w-4 h-4 text-emerald-600" />
              <span>Photo certifiée horodatée</span>
            </span>
            <button
              type="button"
              class="text-xs text-red-600 hover:underline min-h-[32px] px-1"
              @click="photoUploaded = false"
            >
              Supprimer
            </button>
          </div>
          <div class="text-[11px] font-mono text-emerald-800 break-all bg-emerald-100/60 p-1.5 rounded">
            ID: {{ uploadId }}
          </div>
          <div class="text-[10px] font-mono text-cortex-text-muted">
            SHA-256: {{ sha256Hash }}
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-center gap-2">
        <AlertTriangle class="w-4 h-4 shrink-0 text-red-600" />
        <span>{{ errorMessage }}</span>
      </div>

      <!-- Action Footer -->
      <div class="flex items-center justify-end gap-3 pt-3 border-t border-cortex-border">
        <button
          type="button"
          class="px-4 py-2.5 rounded-xl border border-cortex-border bg-cortex-surface hover:bg-cortex-surface-muted text-xs font-semibold text-cortex-text-secondary transition-colors min-h-[44px]"
          @click="handleClose"
        >
          {{ $t('common.cancel', 'Annuler') }}
        </button>
        <button
          type="button"
          class="px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow transition-colors min-h-[44px] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="isSubmitting || !description.trim()"
          @click="handleSubmit"
        >
          <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
          <span>{{ $t('checkin.confirm_damage_btn', 'Enregistrer le constat') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AlertTriangle, Camera, CheckCircle, Loader2, X } from 'lucide-vue-next'
import { getCortexApiClient } from '@/api'

const props = defineProps<{
  isOpen: boolean
  rentalId: string
  serialNumber: string
  itemName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submitted', data: { serialNumber: string; severity: 'minor' | 'major' | 'unusable'; description: string; photoUploadId: string }): void
}>()

const severity = ref<'minor' | 'major' | 'unusable'>('major')
const description = ref('')
const photoUploaded = ref(false)
const uploadId = ref('')
const sha256Hash = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

function simulatePhotoUpload() {
  uploadId.value = `upl-dmg-${Date.now()}`
  sha256Hash.value = `sha256-${Math.random().toString(36).substring(2, 10)}${Math.random().toString(36).substring(2, 10)}9fbf4c89`
  photoUploaded.value = true
}

function handleClose() {
  description.value = ''
  photoUploaded.value = false
  errorMessage.value = ''
  emit('close')
}

async function handleSubmit() {
  if (!description.value.trim()) {
    errorMessage.value = 'Veuillez saisir une description du dommage.'
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    const client = getCortexApiClient()
    const activeUploadId = photoUploaded.value ? uploadId.value : `upl-manual-${Date.now()}`
    
    const res = await client.addDamageEvidence({
      rental_id: props.rentalId,
      serial_number: props.serialNumber,
      severity: severity.value,
      description: description.value.trim(),
      photo_upload_id: activeUploadId
    })

    if (res.status === 'completed') {
      emit('submitted', {
        serialNumber: props.serialNumber,
        severity: severity.value,
        description: description.value.trim(),
        photoUploadId: activeUploadId
      })
      handleClose()
    } else {
      errorMessage.value = res.errors?.[0]?.message || 'Échec de l’enregistrement du dommage.'
    }
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Erreur réseau inattendue.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
