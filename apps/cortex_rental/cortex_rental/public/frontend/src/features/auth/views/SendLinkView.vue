<template>
  <AuthShell :title="title" :lead="sent ? undefined : lead">
    <template v-if="!sent">
      <form class="cxa__stack" novalidate @submit.prevent="submit">
        <div v-if="alert" class="cxa__alert" role="alert">{{ alert }}</div>
        <div>
          <FormControl v-model="email" label="Adresse courriel" type="email" size="md" variant="outline" autocomplete="username" placeholder="nom@entreprise.com" :aria-invalid="error ? 'true' : undefined">
            <template #prefix><Mail :size="16" aria-hidden="true" /></template>
          </FormControl>
          <p v-if="error" class="cxa__error" role="alert">{{ error }}</p>
        </div>
        <Button type="submit" variant="solid" theme="blue" class="cxa__btn cxa__btn--primary" :loading="busy" loading-text="Envoi…">{{ action }}</Button>
      </form>
      <p class="cxa__back"><RouterLink :to="{ name: 'login', query: route.query }">← Retour à la connexion</RouterLink></p>
    </template>

    <div v-else ref="sentEl" tabindex="-1" data-test="auth-sent">
      <MailCheck class="cxa__sent-icon" :size="40" :stroke-width="1.6" aria-hidden="true" />
      <h2 class="cxa__sent-title">Vérifiez votre courriel</h2>
      <p>Si un compte existe pour <strong>{{ email }}</strong>, un message vient d'y être envoyé. {{ sentDetail }}</p>
      <p class="cxa__hint">Rien dans votre boîte de réception ? Vérifiez les indésirables.</p>
      <div v-if="alert" :class="['cxa__alert', notice ? 'cxa__alert--ok' : '']" role="alert">{{ alert }}</div>
      <div class="cxa__stack cxa__stack--tight" style="margin-top: 20px">
        <Button variant="outline" class="cxa__btn cxa__btn--outline" :disabled="cooldown.remaining.value > 0 || busy" @click="resend">
          {{ cooldown.remaining.value > 0 ? `Renvoyer le lien (${cooldown.remaining.value} s)` : 'Renvoyer le lien' }}
        </Button>
        <Button variant="outline" class="cxa__btn cxa__btn--outline" @click="edit">Modifier l'adresse</Button>
      </div>
      <p class="cxa__back"><RouterLink :to="{ name: 'login', query: route.query }">← Retour à la connexion</RouterLink></p>
    </div>
  </AuthShell>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Button, FormControl } from 'frappe-ui'
import { Mail, MailCheck } from 'lucide-vue-next'
import AuthShell from '@/features/auth/components/AuthShell.vue'
import { failureMessage, isEmail, sendLoginLink, sendResetLink } from '@/features/auth/authApi'
import { useCooldown } from '@/features/auth/composables/useCooldown'

// One screen, two flows: `reset` (forgot password) and `login` (one-time sign-in link).
const props = defineProps<{ kind: 'reset' | 'login' }>()
const route = useRoute()
const cooldown = useCooldown(60)

const email = ref('')
const error = ref('')
const alert = ref('')
const notice = ref(false)
const busy = ref(false)
const sent = ref(false)
const sentEl = ref<HTMLElement | null>(null)

const title = computed(() => (props.kind === 'reset' ? 'Mot de passe oublié' : 'Recevoir un lien de connexion'))
const lead = computed(() => (props.kind === 'reset' ? 'Entrez votre adresse courriel et nous vous enverrons un lien pour créer un nouveau mot de passe.' : 'Entrez votre adresse courriel et nous vous enverrons un lien qui vous connecte sans mot de passe.'))
const action = 'Envoyer le lien'
const sentDetail = computed(() => (props.kind === 'reset' ? 'Le lien est à usage unique.' : 'Le lien est à usage unique et expire rapidement.'))

const send = () => (props.kind === 'reset' ? sendResetLink(email.value.trim()) : sendLoginLink(email.value.trim()))

async function submit() {
  error.value = ''
  alert.value = ''
  if (!isEmail(email.value)) {
    error.value = 'Saisissez une adresse courriel valide, par exemple nom@entreprise.com.'
    return
  }
  busy.value = true
  try {
    await send()
    sent.value = true
    cooldown.start()
    await nextTick()
    sentEl.value?.focus()
  } catch (failure) {
    alert.value = failureMessage(failure)
  } finally {
    busy.value = false
  }
}

async function resend() {
  busy.value = true
  alert.value = ''
  notice.value = false
  try {
    await send()
    notice.value = true
    alert.value = `Lien renvoyé à ${email.value.trim()}.`
    cooldown.start()
  } catch (failure) {
    alert.value = failureMessage(failure)
  } finally {
    busy.value = false
  }
}

function edit() {
  sent.value = false
  alert.value = ''
}
</script>
