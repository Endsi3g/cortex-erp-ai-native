<template>
  <AuthShell title="Se connecter à Cortex" lead="Retrouvez vos locations, vos sorties et vos retours.">
    <div class="cxa__stack">
      <div v-if="loginError" class="cxa__alert" role="alert" data-test="login-error">
        {{ loginError }}
        <template v-if="twoFactor"> <a :href="classicLoginUrl">Ouvrir la connexion classique</a>.</template>
      </div>

      <div v-if="hasAlternatives" class="cxa__stack cxa__stack--tight" data-test="login-alternatives">
        <a
          v-for="provider in options?.providers"
          :key="provider.name"
          :href="provider.url"
          class="cxa__btn cxa__btn--outline"
          :class="`cxa__btn--${provider.name}`"
        >
          <img v-if="provider.icon" :src="provider.icon" alt="" />
          Continuer avec {{ provider.label }}
        </a>
        <RouterLink v-if="options?.email_link" :to="{ name: 'login-link', query: route.query }" class="cxa__btn cxa__btn--outline">Recevoir un lien de connexion</RouterLink>
        <p v-if="options?.password_login" class="cxa__divider" aria-hidden="true">ou</p>
      </div>

      <form v-if="options?.password_login !== false" class="cxa__stack" novalidate @submit.prevent="submit">
        <FormControl v-model="usr" label="Adresse courriel" type="text" size="md" variant="outline" autocomplete="username" placeholder="nom@entreprise.com" :aria-invalid="fieldError ? 'true' : undefined">
          <template #prefix><Mail :size="16" aria-hidden="true" /></template>
        </FormControl>

        <div>
          <FormControl v-model="pwd" label="Mot de passe" :type="showPassword ? 'text' : 'password'" size="md" variant="outline" autocomplete="current-password" placeholder="•••••" :aria-invalid="fieldError ? 'true' : undefined">
            <template #prefix><Lock :size="16" aria-hidden="true" /></template>
            <template #suffix>
              <button type="button" class="cxa__toggle" :aria-pressed="showPassword" @click="showPassword = !showPassword">{{ showPassword ? 'Masquer' : 'Afficher' }}</button>
            </template>
          </FormControl>
          <p v-if="fieldError" class="cxa__error" role="alert">{{ fieldError }}</p>
        </div>

        <p class="cxa__row"><RouterLink :to="{ name: 'forgot-password', query: route.query }">Mot de passe oublié ?</RouterLink></p>

        <Button type="submit" variant="solid" theme="blue" class="cxa__btn cxa__btn--primary" :loading="busy" loading-text="Connexion…" data-test="login-submit">Se connecter</Button>
      </form>

      <p v-if="options?.signup_enabled" class="cxa__foot">
        Vous n’avez pas encore de compte ?
        <RouterLink :to="{ name: 'request-access' }">Demander l'accès</RouterLink>
      </p>
    </div>
  </AuthShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Button, FormControl } from 'frappe-ui'
import { Lock, Mail } from 'lucide-vue-next'
import AuthShell from '@/features/auth/components/AuthShell.vue'
import { fetchLoginOptions, signIn, type LoginOptions } from '@/features/auth/authApi'
import { landingUrl, redirectTarget } from '@/features/auth/landing'

const route = useRoute()
const options = ref<LoginOptions | null>(null)
const usr = ref('')
const pwd = ref('')
const showPassword = ref(false)
const busy = ref(false)
const loginError = ref('')
const fieldError = ref('')
const twoFactor = ref(false)

const target = computed(() => redirectTarget(route.query.redirect))
const classicLoginUrl = computed(() => `/login?redirect-to=${encodeURIComponent(landingUrl(target.value))}`)
const hasAlternatives = computed(() => Boolean(options.value && (options.value.providers.length || options.value.email_link)))

onMounted(async () => {
  options.value = await fetchLoginOptions(landingUrl(target.value))
})

async function submit() {
  if (busy.value) return
  loginError.value = ''
  fieldError.value = ''
  twoFactor.value = false
  if (!usr.value.trim() || !pwd.value) {
    fieldError.value = 'Saisissez votre adresse courriel et votre mot de passe.'
    return
  }
  busy.value = true
  const outcome = await signIn(usr.value.trim(), pwd.value)
  if (outcome.ok) {
    // Full page load: the new session needs a fresh CSRF token, which the server writes into the page.
    window.location.assign(landingUrl(target.value))
    return
  }
  busy.value = false
  if (outcome.reason === 'two_factor') {
    twoFactor.value = true
    loginError.value = 'Ce compte exige une vérification en deux étapes.'
  } else if (outcome.reason === 'rate_limited') {
    loginError.value = 'Trop de tentatives. Patientez quelques minutes avant de réessayer.'
  } else if (outcome.reason === 'network') {
    loginError.value = 'La connexion au serveur a échoué. Vos informations sont conservées : réessayez dans un instant.'
  } else {
    fieldError.value = 'Adresse courriel ou mot de passe incorrect.'
  }
}
</script>
