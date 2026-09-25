<template>
  <main class="min-h-screen w-full flex items-center justify-center bg-cortex-bg px-4 font-sans antialiased">
    <section class="w-full max-w-md rounded-2xl border border-cortex-border bg-white p-8 shadow-xl space-y-6">
      <header class="flex flex-col items-center text-center space-y-2"><CortexLogo :collapsed="false" /><h1 class="mt-2 text-lg font-bold text-cortex-text-primary">Connexion au cockpit Cortex</h1><p class="text-xs text-cortex-text-muted">Utilisez votre compte Frappe / ERPNext.</p></header>
      <form class="space-y-4 text-xs" @submit.prevent="handleLogin"><label class="block font-semibold">Identifiant ou courriel<input v-model="email" type="text" autocomplete="username" required class="mt-1 w-full rounded-xl border border-cortex-border px-3 py-2.5" /></label><label class="block font-semibold">Mot de passe<input v-model="password" type="password" autocomplete="current-password" required class="mt-1 w-full rounded-xl border border-cortex-border px-3 py-2.5" /></label><p v-if="errorMessage" class="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">{{ errorMessage }}</p><button type="submit" :disabled="isSubmitting" class="w-full rounded-xl bg-cortex-primary-600 py-2.5 text-xs font-bold text-white hover:bg-cortex-primary-700 disabled:opacity-50">{{ isSubmitting ? 'Connexion…' : 'Se connecter' }}</button></form>
      <footer class="border-t border-cortex-border pt-4 text-center text-[11px] text-cortex-text-muted">Authentification, rôles et accès pilotés par ERPNext.</footer>
    </section>
  </main>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import CortexLogo from '@/app/layouts/components/CortexLogo.vue'
const router = useRouter(); const session = useSessionStore(); const email = ref(''); const password = ref(''); const isSubmitting = ref(false); const errorMessage = ref('')
async function handleLogin() {
  if (isSubmitting.value) return
  isSubmitting.value = true; errorMessage.value = ''
  try {
    const body = new URLSearchParams({ usr: email.value, pwd: password.value })
    const response = await fetch('/api/method/login', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body })
    const result = await response.json().catch(() => ({}))
    if (!response.ok || result.message !== 'Logged In') throw new Error(result.message || 'Identifiant ou mot de passe invalide.')
    if (!(await session.initializeSession())) throw new Error('La session Frappe a été ouverte, mais le profil Cortex est inaccessible.')
    await router.push(typeof router.currentRoute.value.query.redirect === 'string' ? router.currentRoute.value.query.redirect : '/operations')
  } catch (error) { errorMessage.value = error instanceof Error ? error.message : 'Connexion impossible.' }
  finally { isSubmitting.value = false }
}
</script>
