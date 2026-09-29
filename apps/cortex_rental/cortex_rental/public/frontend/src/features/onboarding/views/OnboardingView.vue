<template>
  <div class="cx-page" data-test="screen-onboarding">
    <CortexPageHeader title="Configurer votre entreprise" subtitle="Quatre étapes courtes. Votre progression est enregistrée : vous pouvez fermer la page et reprendre plus tard." :provenance="state?.provenance" />

    <div v-if="error && !state" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-else-if="loading && !state" class="cx-section"><CortexSkeleton variant="table-row" :count="4" /></div>

    <template v-else-if="state">
      <section v-if="active !== 'done'" class="cx-section" aria-label="Progression">
        <p class="m-0 text-sm" style="color: var(--erp-muted)">
          <strong style="color: var(--erp-text)">{{ state.progress.done }} sur {{ state.progress.total }}</strong> étapes terminées
          <span v-if="remainingLabel"> · {{ remainingLabel }}</span>
        </p>
        <div class="cx-bar" role="progressbar" aria-label="Progression de la configuration" :aria-valuenow="state.progress.done" aria-valuemin="0" :aria-valuemax="state.progress.total">
          <span :style="{ width: `${(state.progress.done / state.progress.total) * 100}%` }" />
        </div>
      </section>

      <div v-if="active !== 'done'" class="cx-onb">
        <nav aria-label="Étapes de configuration">
          <ol class="cx-onb__steps">
            <li v-for="(step, index) in state.steps" :key="step.key">
              <button type="button" class="cx-onb__step" :class="{ 'is-active': active === step.key, 'is-done': step.done }" :aria-current="active === step.key ? 'step' : undefined" @click="go(step.key)">
                <span class="cx-onb__mark" aria-hidden="true">{{ step.done ? '✓' : index + 1 }}</span>
                <span>{{ step.title }}<small v-if="step.optional"> · facultatif</small></span>
              </button>
            </li>
            <li>
              <button type="button" class="cx-onb__step" :class="{ 'is-active': active === 'review' }" :disabled="!profileDone" @click="go('review')">
                <span class="cx-onb__mark" aria-hidden="true">{{ state.steps.length + 1 }}</span>
                <span>Terminer</span>
              </button>
            </li>
          </ol>
        </nav>

        <section class="cx-onb__panel" :aria-labelledby="`onb-${active}`">
          <div v-if="notice" class="cx-notice" role="status"><div>{{ notice }}</div></div>
          <div v-if="formError" class="cx-notice cx-notice--error" role="alert"><div>{{ formError }}</div></div>

          <!-- 1. Profil -->
          <form v-if="active === 'profile'" novalidate @submit.prevent="saveProfile">
            <h2 id="onb-profile">Profil de l'entreprise</h2>
            <p class="cx-caption" style="padding: 0 0 16px">Ces informations servent aux devis, aux factures et aux rapports. Vous pourrez les modifier plus tard.</p>
            <div class="cx-form">
              <label class="cx-form__field"><span>Nom légal</span><input class="cx-field" :value="state.profile.company_name" disabled /></label>
              <label class="cx-form__field"><span>Pays</span>
                <select v-model="form.country" class="cx-field" required><option v-for="c in choices?.countries ?? [form.country]" :key="c" :value="c">{{ c }}</option></select>
              </label>
              <label class="cx-form__field"><span>Devise</span>
                <select v-model="form.default_currency" class="cx-field" required><option v-for="c in choices?.currencies ?? [form.default_currency]" :key="c" :value="c">{{ c }}</option></select>
                <small>Non modifiable une fois les premières écritures comptables enregistrées.</small>
              </label>
              <label class="cx-form__field"><span>Fuseau horaire</span>
                <select v-model="form.time_zone" class="cx-field"><option v-for="z in zones" :key="z" :value="z">{{ z }}</option></select>
              </label>
              <label class="cx-form__field"><span>Langue de l'interface</span>
                <select v-model="form.language" class="cx-field"><option v-for="l in choices?.languages ?? []" :key="l.name" :value="l.name">{{ l.label }}</option></select>
              </label>
              <label class="cx-form__field"><span>Numéro de taxes <em>(facultatif)</em></span><input v-model="form.tax_id" class="cx-field" autocomplete="off" placeholder="TPS/TVQ" /></label>
              <label class="cx-form__field"><span>Téléphone <em>(facultatif)</em></span><input v-model="form.phone_no" class="cx-field" type="tel" autocomplete="tel" /></label>
              <label class="cx-form__field"><span>Site web <em>(facultatif)</em></span><input v-model="form.website" class="cx-field" type="url" placeholder="entreprise.com" /></label>
            </div>
            <div class="cx-onb__actions"><button class="cx-btn-primary" type="submit" :disabled="busy">{{ busy ? 'Enregistrement…' : 'Enregistrer et continuer' }}</button></div>
          </form>

          <!-- 2. Équipe -->
          <div v-else-if="active === 'team'">
            <h2 id="onb-team">Invitez votre équipe</h2>
            <p class="cx-caption" style="padding: 0 0 16px">Chaque personne reçoit un courriel pour choisir son mot de passe. Vous choisissez ce qu'elle peut faire ; vous pouvez inviter d'autres personnes plus tard.</p>
            <ul v-if="state.team.length" class="cx-list" aria-label="Membres">
              <li v-for="m in state.team" :key="m.email"><span>{{ m.full_name || m.email }}<small class="block" style="color: var(--erp-muted)">{{ m.email }}</small></span><span class="cx-tag">{{ m.signed_in ? 'Connecté' : 'Invitation envoyée' }}</span></li>
            </ul>
            <form novalidate class="cx-form" @submit.prevent="invite">
              <label class="cx-form__field"><span>Nom complet</span><input v-model="invitee.full_name" class="cx-field" autocomplete="off" /></label>
              <label class="cx-form__field"><span>Courriel</span><input v-model="invitee.email" class="cx-field" type="email" autocomplete="off" /></label>
              <fieldset class="cx-form__field cx-form__field--wide">
                <legend>Ce que cette personne fait</legend>
                <label v-for="p in state.role_presets" :key="p.key" class="cx-radio"><input v-model="invitee.preset" type="radio" name="preset" :value="p.key" /><span><strong>{{ p.label }}</strong><small class="block">{{ p.description }}</small></span></label>
              </fieldset>
              <div class="cx-form__field cx-form__field--wide"><button class="cx-btn-secondary" type="submit" :disabled="busy">{{ busy ? 'Envoi…' : 'Envoyer l\'invitation' }}</button></div>
            </form>
            <div class="cx-onb__actions">
              <button class="cx-btn-primary" type="button" :disabled="busy" @click="completeStep('team')">{{ state.team.length > 1 ? 'Continuer' : 'Continuer sans inviter personne' }}</button>
            </div>
          </div>

          <!-- 3. Catalogue -->
          <div v-else-if="active === 'catalog'">
            <h2 id="onb-catalog">Ajoutez votre matériel</h2>
            <p class="cx-caption" style="padding: 0 0 16px">
              <template v-if="state.catalog.equipment_count">Votre catalogue contient déjà <strong>{{ state.catalog.equipment_count }}</strong> équipement(s).</template>
              <template v-else>Votre catalogue est vide. Importez un fichier ou ajoutez vos premiers équipements ; rien n'est créé à votre place.</template>
            </p>
            <div class="cx-onb__choices">
              <RouterLink class="cx-btn-secondary" to="/app/cortex-import">Importer un fichier (CSV, Excel)</RouterLink>
              <RouterLink class="cx-btn-secondary" to="/app/cortex-equipment">Ouvrir le catalogue</RouterLink>
            </div>
            <div class="cx-onb__actions">
              <button class="cx-btn-primary" type="button" :disabled="busy" @click="completeStep('catalog')">{{ state.catalog.equipment_count ? 'Continuer' : 'Je le ferai plus tard' }}</button>
            </div>
          </div>

          <!-- 4. Règles -->
          <div v-else-if="active === 'policies'">
            <h2 id="onb-policies">Règles de location</h2>
            <p class="cx-caption" style="padding: 0 0 16px">Nous avons appliqué la règle la plus courante. Vous pouvez la garder telle quelle, la modifier ou en ajouter d'autres.</p>
            <ul class="cx-list" aria-label="Règles actives">
              <li v-for="r in state.policies.rules" :key="r.name"><span>{{ r.rule_name }}<small class="block" style="color: var(--erp-muted)">{{ r.calendar_days }} jours calendaires facturés {{ r.billable_days }}</small></span><span class="cx-tag">Active</span></li>
              <li v-if="!state.policies.rules.length"><span>Aucune règle active : chaque jour est facturé au tarif complet.</span></li>
            </ul>
            <div class="cx-onb__choices"><RouterLink class="cx-btn-secondary" to="/app/cortex-rental-policy">Modifier les règles</RouterLink></div>
            <div class="cx-onb__actions"><button class="cx-btn-primary" type="button" :disabled="busy" @click="completeStep('policies')">Garder ces règles et continuer</button></div>
          </div>

          <!-- Revue -->
          <div v-else-if="active === 'review'">
            <h2 id="onb-review">Tout est prêt ?</h2>
            <ul class="cx-list" aria-label="Récapitulatif">
              <li v-for="s in state.steps" :key="s.key"><span>{{ s.title }}</span><span class="cx-tag">{{ s.done ? 'Terminé' : 'À faire plus tard' }}</span></li>
            </ul>
            <p class="cx-caption" style="padding: 12px 0 0">Les étapes restantes restent accessibles depuis les Paramètres ; rien n'est perdu.</p>
            <div class="cx-onb__actions"><button class="cx-btn-primary" type="button" :disabled="busy" @click="finish">{{ busy ? 'Finalisation…' : 'Terminer la configuration' }}</button></div>
          </div>
        </section>
      </div>

      <!-- Fin -->
      <section v-else class="cx-section cx-onb__done" aria-labelledby="onb-done" tabindex="-1">
        <h2 id="onb-done">Votre espace {{ state.profile.company_name }} est prêt</h2>
        <p>Voici ce qui a été enregistré et par où commencer.</p>
        <ul class="cx-list" aria-label="Ce qui est en place">
          <li v-for="s in state.steps" :key="s.key"><span>{{ s.title }}</span><span class="cx-tag">{{ s.done ? 'Terminé' : 'Passé' }}</span></li>
        </ul>
        <div class="cx-onb__choices">
          <RouterLink class="cx-btn-primary" to="/app/cortex-rental/new">Créer un premier devis</RouterLink>
          <RouterLink class="cx-btn-secondary" to="/app/cortex-equipment">Ajouter du matériel</RouterLink>
          <RouterLink class="cx-btn-secondary" to="/app/cortex-operations">Ouvrir le tableau de bord</RouterLink>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { getCortexApiClient } from '@/api'
import type { OnboardingState, OnboardingWriteResult } from '@/api/contracts'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import { useResource } from '@/features/common/composables/useResource'

type Panel = 'profile' | 'team' | 'catalog' | 'policies' | 'review' | 'done'

const zones = ['America/Toronto', 'America/Halifax', 'America/Winnipeg', 'America/Edmonton', 'America/Vancouver', 'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'Europe/Paris']

const { data: loaded, loading, error, reload } = useResource(async () => {
  const client = getCortexApiClient()
  const [onboarding, options] = await Promise.all([client.getOnboarding(), client.listOnboardingChoices()])
  return { onboarding, options }
})

const state = ref<OnboardingState | null>(null)
const choices = computed(() => loaded.value?.options ?? null)
const active = ref<Panel>('profile')
const busy = ref(false)
const notice = ref('')
const formError = ref('')
const form = reactive({ country: '', default_currency: '', tax_id: '', phone_no: '', website: '', time_zone: 'America/Toronto', language: 'fr' })
const invitee = reactive({ full_name: '', email: '', preset: 'manager' })

const profileDone = computed(() => !!state.value?.steps.find((s) => s.key === 'profile')?.done)
const remainingLabel = computed(() => {
  const left = (state.value?.progress.total ?? 0) - (state.value?.progress.done ?? 0)
  return left > 0 ? `environ ${Math.max(2, left * 2)} minutes restantes` : ''
})

function panelFor(s: OnboardingState): Panel {
  if (s.status === 'Completed') return 'done'
  const current = s.steps.find((step) => step.current)
  return current ? current.key : 'review'
}

watch(loaded, (value) => {
  if (!value) return
  state.value = value.onboarding
  Object.assign(form, {
    country: value.onboarding.profile.country ?? 'Canada',
    default_currency: value.onboarding.profile.default_currency ?? 'CAD',
    tax_id: value.onboarding.profile.tax_id,
    phone_no: value.onboarding.profile.phone_no,
    website: value.onboarding.profile.website,
    time_zone: value.onboarding.profile.time_zone,
    language: value.onboarding.profile.language
  })
  active.value = panelFor(value.onboarding)
})

function go(panel: Panel) {
  notice.value = ''
  formError.value = ''
  active.value = panel
}

function apply(result: OnboardingWriteResult, done = ''): boolean {
  if (!result.ok) {
    formError.value = result.message ?? "L'opération n'a pas pu être enregistrée."
    return false
  }
  if (result.state) state.value = result.state
  if (done) notice.value = done
  return true
}

async function run(action: () => Promise<OnboardingWriteResult>, success = ''): Promise<boolean> {
  busy.value = true
  formError.value = ''
  notice.value = ''
  try {
    return apply(await action(), success)
  } catch (cause) {
    formError.value = cause instanceof Error ? `${cause.message} Vos informations sont conservées : réessayez.` : 'La connexion au serveur a échoué. Vos informations sont conservées : réessayez.'
    return false
  } finally {
    busy.value = false
  }
}

function next() {
  if (state.value) active.value = panelFor(state.value)
}

async function saveProfile() {
  if (!form.country || !form.default_currency) {
    formError.value = 'Choisissez le pays et la devise pour continuer.'
    return
  }
  if (await run(() => getCortexApiClient().saveCompanyProfile({ ...form }))) next()
}

async function invite() {
  if (!invitee.full_name.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(invitee.email.trim())) {
    formError.value = 'Indiquez le nom et un courriel valide (nom@entreprise.com).'
    return
  }
  const email = invitee.email.trim()
  let link = ''
  const ok = await run(async () => {
    const result = await getCortexApiClient().inviteTeamMember({ email, full_name: invitee.full_name.trim(), preset: invitee.preset })
    link = result.setup_link ?? ''
    return result
  })
  if (!ok) return
  state.value = await getCortexApiClient().getOnboarding()
  notice.value = link
    ? `Le courriel n'a pas pu être envoyé. Transmettez ce lien à usage unique à ${email} : ${link}`
    : `Invitation envoyée à ${email}.`
  invitee.full_name = ''
  invitee.email = ''
}

async function completeStep(step: string) {
  if (await run(() => getCortexApiClient().completeOnboardingStep(step))) next()
}

async function finish() {
  if (await run(() => getCortexApiClient().finishOnboarding())) active.value = 'done'
}
</script>
