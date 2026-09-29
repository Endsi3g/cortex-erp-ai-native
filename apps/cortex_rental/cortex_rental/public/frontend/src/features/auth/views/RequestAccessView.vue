<template>
  <AuthShell title="Demander l'accès à Cortex">
    <template v-if="!sent">
      <ol class="cxa__progress" aria-label="Progression de la demande">
        <li :class="step === 1 ? 'is-current' : 'is-done'" :aria-current="step === 1 ? 'step' : undefined"><span>1</span> Vous</li>
        <li :class="step === 2 ? 'is-current' : ''" :aria-current="step === 2 ? 'step' : undefined"><span>2</span> Votre entreprise</li>
      </ol>

      <div v-if="alert" class="cxa__alert" role="alert" style="margin-bottom: 16px">{{ alert }}</div>

      <form class="cxa__stack" novalidate data-test="access-form" @submit.prevent="submit">
        <template v-if="step === 1">
          <div>
            <FormControl v-model="form.full_name" label="Nom complet" size="md" variant="outline" autocomplete="name" placeholder="Camille Tremblay" :aria-invalid="errors.full_name ? 'true' : undefined" />
            <p v-if="errors.full_name" class="cxa__error" role="alert">{{ errors.full_name }}</p>
          </div>
          <div>
            <FormControl v-model="form.email" label="Courriel professionnel" type="email" size="md" variant="outline" autocomplete="username" placeholder="camille@entreprise.com" :aria-invalid="errors.email ? 'true' : undefined">
              <template #prefix><Mail :size="16" aria-hidden="true" /></template>
            </FormControl>
            <p v-if="errors.email" class="cxa__error" role="alert">{{ errors.email }}</p>
            <p v-else class="cxa__hint">Nous y envoyons le lien de confirmation. Les adresses personnelles (Gmail, Outlook…) ne sont pas acceptées.</p>
          </div>
          <Button type="button" variant="solid" theme="blue" class="cxa__btn cxa__btn--primary" @click="next">Continuer</Button>
        </template>

        <template v-else>
          <div>
            <FormControl v-model="form.company_name" label="Nom de l'entreprise" size="md" variant="outline" autocomplete="organization" placeholder="Studio Lumière inc." :aria-invalid="errors.company_name ? 'true' : undefined" />
            <p v-if="errors.company_name" class="cxa__error" role="alert">{{ errors.company_name }}</p>
          </div>
          <FormControl v-model="form.job_title" label="Fonction (facultatif)" size="md" variant="outline" autocomplete="organization-title" placeholder="Directrice des opérations" />
          <fieldset class="cxa__choice">
            <legend>Taille de l'équipe</legend>
            <label v-for="size in sizes" :key="size.value"><input v-model="form.team_size" type="radio" name="team_size" :value="size.value" /> {{ size.label }}</label>
          </fieldset>
          <div>
            <label class="cxa__check"><input v-model="terms" type="checkbox" :aria-invalid="errors.terms ? 'true' : undefined" /> <span>J'accepte les conditions d'utilisation et la politique de confidentialité.</span></label>
            <p v-if="errors.terms" class="cxa__error" role="alert">{{ errors.terms }}</p>
          </div>
          <div class="cxa__hp" aria-hidden="true"><label>Ne pas remplir <input v-model="form.website" type="text" tabindex="-1" autocomplete="off" /></label></div>
          <div class="cxa__actions">
            <Button type="button" variant="outline" class="cxa__btn cxa__btn--outline" @click="back">Retour</Button>
            <Button type="submit" variant="solid" theme="blue" class="cxa__btn cxa__btn--primary" :loading="busy" loading-text="Envoi…" data-test="access-submit">Envoyer la demande</Button>
          </div>
          <p class="cxa__hint">Un administrateur examine chaque demande, habituellement en un jour ouvrable. Rien n'est créé avant votre confirmation par courriel.</p>
        </template>
      </form>
      <p v-if="step === 1" class="cxa__foot">Vous avez déjà un compte ? <RouterLink :to="{ name: 'login' }">Se connecter</RouterLink></p>
    </template>

    <div v-else ref="sentEl" tabindex="-1" data-test="auth-sent">
      <MailCheck class="cxa__sent-icon" :size="40" :stroke-width="1.6" aria-hidden="true" />
      <h2 class="cxa__sent-title">Vérifiez votre courriel</h2>
      <p>Nous avons envoyé un lien de confirmation à <strong>{{ form.email }}</strong>.</p>
      <ol class="cxa__steps">
        <li><strong>Confirmez votre courriel</strong> avec le lien reçu (valide 48 h).</li>
        <li><strong>Nous examinons la demande</strong>, habituellement en un jour ouvrable.</li>
        <li><strong>Choisissez votre mot de passe</strong> : un assistant vous aide à configurer l'entreprise.</li>
      </ol>
      <p class="cxa__hint">Rien dans votre boîte de réception ? Vérifiez les indésirables.</p>
      <div v-if="alert" class="cxa__alert cxa__alert--ok" role="alert" style="margin-top: 12px">{{ alert }}</div>
      <div class="cxa__stack cxa__stack--tight" style="margin-top: 20px">
        <Button variant="outline" class="cxa__btn cxa__btn--outline" :disabled="cooldown.remaining.value > 0 || busy" @click="resend">
          {{ cooldown.remaining.value > 0 ? `Renvoyer le lien (${cooldown.remaining.value} s)` : 'Renvoyer le lien' }}
        </Button>
        <Button variant="outline" class="cxa__btn cxa__btn--outline" @click="edit">Modifier l'adresse</Button>
      </div>
      <p class="cxa__back"><RouterLink :to="{ name: 'login' }">← Retour à la connexion</RouterLink></p>
    </div>
  </AuthShell>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Button, FormControl } from 'frappe-ui'
import { Mail, MailCheck } from 'lucide-vue-next'
import AuthShell from '@/features/auth/components/AuthShell.vue'
import { failureMessage, isEmail, isFreeEmail, requestAccess } from '@/features/auth/authApi'
import { useCooldown } from '@/features/auth/composables/useCooldown'

const sizes = [
  { value: '1', label: 'Moi seul' },
  { value: '2-10', label: '2 à 10' },
  { value: '11-50', label: '11 à 50' },
  { value: '51+', label: '51 et plus' }
]

const cooldown = useCooldown(60)
const step = ref<1 | 2>(1)
const busy = ref(false)
const sent = ref(false)
const alert = ref('')
const terms = ref(false)
const sentEl = ref<HTMLElement | null>(null)
const form = reactive({ full_name: '', email: '', company_name: '', job_title: '', team_size: '2-10', website: '' })
const errors = reactive<Record<string, string>>({ full_name: '', email: '', company_name: '', terms: '' })

function validateStep1(): boolean {
  errors.full_name = form.full_name.trim() ? '' : 'Indiquez votre nom complet.'
  if (!isEmail(form.email)) errors.email = 'Saisissez une adresse courriel valide, par exemple camille@entreprise.com.'
  else if (isFreeEmail(form.email)) errors.email = 'Utilisez votre courriel professionnel : les adresses personnelles ne sont pas acceptées.'
  else errors.email = ''
  return !errors.full_name && !errors.email
}

function validateStep2(): boolean {
  errors.company_name = form.company_name.trim() ? '' : "Indiquez le nom de l'entreprise."
  errors.terms = terms.value ? '' : 'Acceptez les conditions pour envoyer la demande.'
  return !errors.company_name && !errors.terms
}

const payload = () => ({
  full_name: form.full_name.trim(),
  email: form.email.trim().toLowerCase(),
  company_name: form.company_name.trim(),
  job_title: form.job_title.trim(),
  team_size: form.team_size,
  accept_terms: terms.value ? 1 : 0,
  website: form.website
})

function next() {
  alert.value = ''
  if (validateStep1()) step.value = 2
}

function back() {
  alert.value = ''
  step.value = 1
}

const serverFieldStep: Record<string, [string, 1 | 2]> = { invalid_email: ['email', 1], free_email: ['email', 1], domain_not_allowed: ['email', 1], terms: ['terms', 2] }

async function submit() {
  if (step.value === 1) return next()
  if (!validateStep1()) {
    step.value = 1
    return
  }
  if (!validateStep2() || busy.value) return
  busy.value = true
  alert.value = ''
  try {
    const result = await requestAccess(payload())
    if (result.ok) {
      sent.value = true
      cooldown.start()
      await nextTick()
      sentEl.value?.focus()
      return
    }
    const target = serverFieldStep[result.code ?? '']
    if (target) {
      errors[target[0]] = result.message ?? ''
      step.value = target[1]
    } else {
      alert.value = result.message || "La demande n'a pas pu être envoyée."
    }
  } catch (failure) {
    alert.value = failureMessage(failure)
  } finally {
    busy.value = false
  }
}

async function resend() {
  busy.value = true
  alert.value = ''
  try {
    await requestAccess(payload())
    alert.value = `Lien renvoyé à ${form.email.trim()}.`
    cooldown.start()
  } catch (failure) {
    alert.value = failureMessage(failure)
  } finally {
    busy.value = false
  }
}

function edit() {
  sent.value = false
  step.value = 1
  alert.value = ''
}
</script>
