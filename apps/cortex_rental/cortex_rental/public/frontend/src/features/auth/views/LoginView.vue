<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-cortex-bg px-4 font-sans antialiased">
    <div class="w-full max-w-md p-8 rounded-2xl border border-cortex-border bg-cortex-surface shadow-xl space-y-6">
      <div class="flex flex-col items-center text-center space-y-2">
        <CortexLogo :collapsed="false" />
        <h1 class="text-lg font-bold text-cortex-text-primary tracking-tight mt-2">
          Connexion au Cockpit Cortex
        </h1>
        <p class="text-xs text-cortex-text-muted">
          Système d'exploitation de location audiovisuelle et événementielle
        </p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4 text-xs">
        <div>
          <label class="block font-semibold text-cortex-text-primary mb-1">
            Identifiant / E-mail Frappe
          </label>
          <input
            v-model="email"
            type="email"
            class="w-full px-3 py-2 rounded-xl border border-cortex-border bg-cortex-surface-subtle text-cortex-text-primary focus:outline-none focus:ring-2 focus:ring-cortex-primary-500 font-sans"
            placeholder="utilisateur@cortex.local"
            required
          />
        </div>

        <div>
          <label class="block font-semibold text-cortex-text-primary mb-1">
            Mot de passe
          </label>
          <input
            v-model="password"
            type="password"
            class="w-full px-3 py-2 rounded-xl border border-cortex-border bg-cortex-surface-subtle text-cortex-text-primary focus:outline-none focus:ring-2 focus:ring-cortex-primary-500 font-sans"
            placeholder="••••••••"
            required
          />
        </div>

        <button
          type="submit"
          class="w-full py-2.5 rounded-xl bg-cortex-primary-600 text-white font-bold text-xs hover:bg-cortex-primary-700 transition-colors shadow-xs"
        >
          Se connecter
        </button>
      </form>

      <div class="pt-4 border-t border-cortex-border text-center text-[11px] text-cortex-text-muted">
        Mode démonstration actif · Session synthétique pré-configurée
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import CortexLogo from '@/app/layouts/components/CortexLogo.vue'

const router = useRouter()
const sessionStore = useSessionStore()

const email = ref('kael@cortex.local')
const password = ref('••••••••')

const handleLogin = async () => {
  await sessionStore.initializeSession()
  router.push('/app/cortex-operations')
}
</script>
