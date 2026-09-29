<template>
  <div class="cx-page" data-test="screen-rental-policies">
    <CortexPageHeader title="Règles tarifaires" subtitle="Une règle active pour une durée exacte remplace la courbe de référence. Le prix reste calculé par le serveur." :provenance="data?.provenance">
      <template #actions>
        <button v-if="data?.can_edit" type="button" class="cx-btn-primary" data-test="new-rule" @click="startNew">Nouvelle règle</button>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-else-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="4" /></div>

    <template v-else-if="data">
      <div v-if="notice" class="cx-notice" role="status"><div>{{ notice }}</div></div>

      <form v-if="editing" class="cx-section" novalidate data-test="rule-form" @submit.prevent="save">
        <h2 id="rule-form-title">{{ editing.name ? 'Modifier la règle' : 'Nouvelle règle' }}</h2>
        <div v-if="formError && !fieldErrors.length" class="cx-notice cx-notice--error" role="alert"><div>{{ formError }}</div></div>
        <div class="cx-form" aria-labelledby="rule-form-title">
          <label class="cx-form__field cx-form__field--wide"><span>Nom de la règle</span><input v-model="editing.rule_name" class="cx-field" maxlength="100" placeholder="7 jours = 3 jours facturés" :aria-invalid="hasError('rule_name')" /></label>
          <label class="cx-form__field"><span>Jours civils</span><input v-model.number="editing.calendar_days" class="cx-field" type="number" min="1" max="365" inputmode="numeric" :aria-invalid="hasError('calendar_days')" /><small>Durée exacte de la location à laquelle la règle s'applique.</small></label>
          <label class="cx-form__field"><span>Jours facturés</span><input v-model.number="editing.billable_days" class="cx-field" type="number" min="0.5" step="0.5" inputmode="decimal" :aria-invalid="hasError('billable_days')" /><small>Par exemple 3 ou 1,5.</small></label>
          <label class="cx-form__field cx-form__field--wide"><span>Description <em>(facultatif)</em></span><input v-model="editing.description" class="cx-field" maxlength="500" /></label>
          <label class="cx-check cx-form__field--wide"><input v-model="editing.is_active" type="checkbox" /> Règle active</label>
        </div>
        <p v-if="fieldErrors.length" class="cx-notice cx-notice--error" role="alert" style="margin: 12px 0 0"><span>{{ fieldErrors[0] }}</span></p>
        <p class="cx-caption" style="padding: 12px 0 0" data-test="rule-preview">{{ preview }}</p>
        <div class="cx-actions" style="padding-top: 12px">
          <button type="submit" class="cx-btn-primary" :disabled="busy">{{ busy ? 'Enregistrement…' : 'Enregistrer' }}</button>
          <button type="button" class="cx-btn-secondary" :disabled="busy" @click="cancel">Annuler</button>
        </div>
      </form>

      <section class="cx-section" aria-labelledby="rules-title">
        <h2 id="rules-title">Règles de {{ data.company }}</h2>
        <div v-if="!data.rules.length" class="cx-empty"><strong>Aucune règle</strong>La courbe de référence ci-dessous s'applique à toutes les durées.</div>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead><tr><th scope="col">Règle</th><th scope="col" class="num">Jours civils</th><th scope="col" class="num">Jours facturés</th><th scope="col" class="num">Part du plein tarif</th><th scope="col">État</th><th v-if="data.can_edit" scope="col"><span class="sr-only">Actions</span></th></tr></thead>
            <tbody>
              <tr v-for="rule in data.rules" :key="rule.name">
                <td>{{ rule.rule_name }}<div v-if="rule.description" class="text-xs" style="color: var(--erp-muted)">{{ rule.description }}</div></td>
                <td class="num">{{ rule.calendar_days }}</td>
                <td class="num">{{ format(rule.billable_days) }}</td>
                <td class="num">{{ share(rule.billable_days, rule.calendar_days) }}</td>
                <td><span class="cx-tag" :class="rule.is_active ? 'cx-tag--ok' : ''">{{ rule.is_active ? 'Active' : 'Désactivée' }}</span></td>
                <td v-if="data.can_edit" class="num">
                  <button type="button" class="cx-btn-soft" @click="edit(rule)">Modifier</button>
                  <button type="button" class="cx-btn-soft" :disabled="busy" @click="toggle(rule)">{{ rule.is_active ? 'Désactiver' : 'Activer' }}</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!data.can_edit" class="cx-caption" style="padding: 12px 0 0">Votre rôle permet de consulter les règles, pas de les modifier.</p>
      </section>

      <section class="cx-section" aria-labelledby="curve-title">
        <h2 id="curve-title">Courbe de référence</h2>
        <p class="cx-caption" style="padding: 0 0 12px">Appliquée quand aucune règle active ne correspond exactement à la durée. Valeurs calculées par le serveur.</p>
        <div class="cx-tablewrap">
          <table class="cx-table" aria-label="Courbe de référence">
            <thead><tr><th scope="col">Jours civils</th><th scope="col" class="num">Jours facturés</th><th scope="col" class="num">Part du plein tarif</th></tr></thead>
            <tbody>
              <tr v-for="point in data.reference_curve" :key="point.calendar_days"><td>{{ point.calendar_days }}</td><td class="num">{{ format(point.billable_days) }}</td><td class="num">{{ share(point.billable_days, point.calendar_days) }}</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { getCortexApiClient } from '@/api'
import type { PricingRule } from '@/api/contracts'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

interface Draft { name?: string; rule_name: string; calendar_days: number; billable_days: number; description: string; is_active: boolean }

const { data, loading, error, reload } = useResource(() => getCortexApiClient().getPricing())
const editing = ref<Draft | null>(null)
const busy = ref(false)
const notice = ref('')
const formError = ref('')
const errorCode = ref('')
const fieldErrors = reactive<string[]>([])

const format = (value: number) => new Intl.NumberFormat('fr-CA', { maximumFractionDigits: 2 }).format(value)
const share = (billable: number, calendar: number) => (calendar > 0 ? `${Math.round((billable / calendar) * 100)} %` : '—')
const codeFields: Record<string, string> = { required: 'rule_name', invalid_characters: 'rule_name', invalid_days: 'calendar_days', duplicate_rule: 'calendar_days', invalid_billable: 'billable_days', billable_exceeds_calendar: 'billable_days' }
const hasError = (field: string) => (codeFields[errorCode.value] === field ? 'true' : undefined)

const preview = computed(() => {
  const d = editing.value
  if (!d || !(d.calendar_days > 0) || !(d.billable_days > 0)) return 'Indiquez les jours civils et les jours facturés pour voir l’effet de la règle.'
  return `Une location de ${d.calendar_days} jour${d.calendar_days > 1 ? 's' : ''} civil${d.calendar_days > 1 ? 's' : ''} est facturée ${format(d.billable_days)} jour${d.billable_days > 1 ? 's' : ''}, soit ${share(d.billable_days, d.calendar_days)} du plein tarif.`
})

function startNew() {
  clearErrors()
  editing.value = { rule_name: '', calendar_days: 7, billable_days: 3, description: '', is_active: true }
}
function edit(rule: PricingRule) {
  clearErrors()
  editing.value = { name: rule.name, rule_name: rule.rule_name, calendar_days: rule.calendar_days, billable_days: rule.billable_days, description: rule.description, is_active: rule.is_active }
}
function cancel() {
  editing.value = null
  clearErrors()
}
function clearErrors() {
  formError.value = ''
  errorCode.value = ''
  fieldErrors.splice(0)
}

async function save() {
  if (!editing.value || busy.value) return
  clearErrors()
  busy.value = true
  try {
    const result = await getCortexApiClient().savePricingRule({ ...editing.value })
    if (!result.ok || !result.state) {
      errorCode.value = result.code ?? ''
      fieldErrors.push(result.message ?? 'La règle n’a pas pu être enregistrée.')
      return
    }
    data.value = result.state
    notice.value = 'Règle enregistrée.'
    editing.value = null
  } catch (cause) {
    formError.value = cause instanceof Error ? cause.message : 'Enregistrement impossible.'
  } finally {
    busy.value = false
  }
}

async function toggle(rule: PricingRule) {
  busy.value = true
  notice.value = ''
  try {
    const result = await getCortexApiClient().setPricingRuleActive(rule.name, !rule.is_active)
    if (result.ok && result.state) {
      data.value = result.state
      notice.value = rule.is_active ? 'Règle désactivée : la courbe de référence s’applique à cette durée.' : 'Règle activée.'
    } else notice.value = result.message ?? 'Le changement n’a pas pu être appliqué.'
  } catch (cause) {
    notice.value = cause instanceof Error ? cause.message : 'Le changement n’a pas pu être appliqué.'
  } finally {
    busy.value = false
  }
}
</script>
