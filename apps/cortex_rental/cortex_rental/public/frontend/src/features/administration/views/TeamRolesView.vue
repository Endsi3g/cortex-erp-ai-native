<template>
  <div class="cx-page" data-test="screen-team-roles">
    <CortexPageHeader title="Équipe et rôles" subtitle="Chaque profil regroupe des rôles Cortex. Les changements sont enregistrés au journal d'audit." :provenance="data?.provenance">
      <template #actions>
        <button v-if="data?.can_manage" type="button" class="cx-btn-primary" data-test="invite-toggle" @click="inviting = !inviting">{{ inviting ? 'Fermer' : 'Inviter une personne' }}</button>
        <RefreshButton :loading="loading" @refresh="reload" />
      </template>
    </CortexPageHeader>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-else-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="4" /></div>

    <template v-else-if="data">
      <div v-if="notice" class="cx-notice" :class="{ 'cx-notice--error': noticeIsError }" :role="noticeIsError ? 'alert' : 'status'"><div>{{ notice }}</div></div>
      <div v-if="setupLink" class="cx-notice" role="status"><div>Le courriel n'a pas pu partir. Transmettez ce lien à usage unique à la personne : <code class="break-all">{{ setupLink }}</code></div></div>

      <form v-if="inviting" class="cx-section" novalidate data-test="invite-form" @submit.prevent="invite">
        <h2 id="invite-title">Inviter une personne</h2>
        <div class="cx-form" aria-labelledby="invite-title">
          <label class="cx-form__field"><span>Nom complet</span><input v-model="invitee.full_name" class="cx-field" autocomplete="off" /></label>
          <label class="cx-form__field"><span>Courriel</span><input v-model="invitee.email" class="cx-field" type="email" autocomplete="off" /></label>
          <fieldset class="cx-form__field cx-form__field--wide">
            <legend>Ce que cette personne fait</legend>
            <label v-for="p in data.presets" :key="p.key" class="cx-radio"><input v-model="invitee.preset" type="radio" name="invite-preset" :value="p.key" /><span><strong>{{ p.label }}</strong><small class="block">{{ p.description }}</small></span></label>
          </fieldset>
        </div>
        <p v-if="inviteError" class="cx-notice cx-notice--error" role="alert" style="margin: 12px 0 0"><span>{{ inviteError }}</span></p>
        <div class="cx-actions" style="padding-top: 12px"><button type="submit" class="cx-btn-primary" :disabled="busy">{{ busy ? 'Envoi…' : 'Envoyer l\'invitation' }}</button></div>
      </form>

      <section class="cx-section" aria-labelledby="members-title">
        <h2 id="members-title">Équipe de {{ data.company }}</h2>
        <div v-if="!data.members.length" class="cx-empty"><strong>Aucun membre</strong>Invitez une première personne.</div>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead><tr><th scope="col">Personne</th><th scope="col">Profil</th><th scope="col">État</th><th scope="col">Dernière connexion</th><th v-if="data.can_manage" scope="col"><span class="sr-only">Actions</span></th></tr></thead>
            <tbody>
              <tr v-for="m in data.members" :key="m.email" :class="{ 'opacity-60': !m.enabled }">
                <td>{{ m.full_name }}<span v-if="m.is_you" class="cx-tag" style="margin-left: 8px">Vous</span><div class="text-xs" style="color: var(--erp-muted)">{{ m.email }}</div></td>
                <td>
                  <span v-if="m.is_owner" class="cx-tag cx-tag--ok">Propriétaire</span>
                  <select v-else-if="data.can_manage" class="cx-field" :aria-label="`Profil de ${m.full_name}`" :value="m.preset ?? ''" :disabled="busy" @change="changePreset(m, ($event.target as HTMLSelectElement).value)">
                    <option v-if="!m.preset" value="" disabled>Personnalisé</option>
                    <option v-for="p in data.presets" :key="p.key" :value="p.key">{{ p.label }}</option>
                  </select>
                  <span v-else>{{ presetLabel(m.preset) }}</span>
                </td>
                <td><span class="cx-tag" :class="stateClass(m)">{{ stateLabel(m) }}</span></td>
                <td>{{ m.last_login ? formatDate(m.last_login) : '—' }}</td>
                <td v-if="data.can_manage" class="num">
                  <template v-if="m.is_owner || m.is_you"><span class="text-xs" style="color: var(--erp-muted)">—</span></template>
                  <template v-else-if="confirming === m.email">
                    <button type="button" class="cx-btn-primary" :disabled="busy" @click="setEnabled(m, false)">Confirmer</button>
                    <button type="button" class="cx-btn-soft" @click="confirming = ''">Annuler</button>
                  </template>
                  <button v-else-if="m.enabled" type="button" class="cx-btn-soft" @click="confirming = m.email">Désactiver</button>
                  <button v-else type="button" class="cx-btn-soft" :disabled="busy" @click="setEnabled(m, true)">Réactiver</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!data.can_manage" class="cx-caption" style="padding: 12px 0 0">Seul le propriétaire de l'entreprise peut modifier l'équipe.</p>
      </section>

      <section class="cx-section" aria-labelledby="presets-title">
        <h2 id="presets-title">Profils disponibles</h2>
        <dl class="cx-dl"><div v-for="p in data.presets" :key="p.key"><dt>{{ p.label }}</dt><dd>{{ p.description }}</dd></div></dl>
        <p class="cx-caption" style="padding: 12px 0 0">Aucun profil ne donne les droits d'administrateur du système. Une personne désactivée ne peut plus se connecter ; son historique est conservé.</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { getCortexApiClient } from '@/api'
import type { TeamMember, TeamState } from '@/api/contracts'
import { formatDate } from '@/app/i18n/formatters'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const { data, loading, error, reload } = useResource(() => getCortexApiClient().getTeam())
const busy = ref(false)
const inviting = ref(false)
const confirming = ref('')
const notice = ref('')
const noticeIsError = ref(false)
const setupLink = ref('')
const inviteError = ref('')
const invitee = reactive({ full_name: '', email: '', preset: 'manager' })

const presetLabel = (key: string | null) => data.value?.presets.find((p) => p.key === key)?.label ?? 'Personnalisé'
const stateLabel = (m: TeamMember) => (!m.enabled ? 'Désactivé' : m.signed_in ? 'Actif' : 'Invitation envoyée')
const stateClass = (m: TeamMember) => (!m.enabled ? 'cx-tag--bad' : m.signed_in ? 'cx-tag--ok' : 'cx-tag--warn')

function say(message: string, isError = false) {
  notice.value = message
  noticeIsError.value = isError
}

async function apply(run: () => Promise<{ ok: boolean; message?: string; state?: TeamState }>, success: string) {
  busy.value = true
  say('')
  try {
    const result = await run()
    if (result.ok && result.state) {
      data.value = result.state
      say(success)
    } else say(result.message ?? 'Le changement n’a pas pu être appliqué.', true)
  } catch (cause) {
    say(cause instanceof Error ? cause.message : 'Le changement n’a pas pu être appliqué.', true)
  } finally {
    busy.value = false
    confirming.value = ''
  }
}

const changePreset = (m: TeamMember, preset: string) => apply(() => getCortexApiClient().setMemberPreset(m.email, preset), `Profil de ${m.full_name} mis à jour.`)
const setEnabled = (m: TeamMember, enabled: boolean) => apply(() => getCortexApiClient().setMemberEnabled(m.email, enabled), enabled ? `${m.full_name} peut de nouveau se connecter.` : `${m.full_name} ne peut plus se connecter.`)

async function invite() {
  if (busy.value) return
  inviteError.value = ''
  setupLink.value = ''
  if (!invitee.full_name.trim() || !invitee.email.trim()) {
    inviteError.value = 'Indiquez le nom et le courriel de la personne.'
    return
  }
  busy.value = true
  try {
    const result = await getCortexApiClient().inviteTeamMember({ ...invitee })
    if (!result.ok) {
      inviteError.value = result.message ?? 'L’invitation n’a pas pu être envoyée.'
      return
    }
    setupLink.value = result.setup_link ?? ''
    say(result.email_sent ? `Invitation envoyée à ${result.email}.` : `Compte créé pour ${result.email}.`)
    invitee.full_name = ''
    invitee.email = ''
    inviting.value = false
    await reload()
  } catch (cause) {
    inviteError.value = cause instanceof Error ? cause.message : 'L’invitation n’a pas pu être envoyée.'
  } finally {
    busy.value = false
  }
}
</script>
