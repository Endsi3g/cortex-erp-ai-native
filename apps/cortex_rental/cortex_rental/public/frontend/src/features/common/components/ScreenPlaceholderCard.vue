<template>
  <div class="max-w-6xl mx-auto space-y-6 font-sans antialiased">
    <!-- Header Card -->
    <div class="p-6 rounded-2xl border border-cortex-border bg-cortex-surface shadow-xs space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-cortex-border pb-4">
        <div class="flex items-center gap-3">
          <div class="flex items-center justify-center w-12 h-12 rounded-xl bg-cortex-primary-50 text-cortex-primary-700 border border-cortex-primary-200 shadow-2xs">
            <component :is="iconComponent" class="w-6 h-6" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-cortex-ink-900 text-white">
                Écran #{{ screenId }}
              </span>
              <span
                class="text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wider"
                :class="priorityBadgeClass"
              >
                {{ priority }}
              </span>
              <span class="text-xs font-medium px-2 py-0.5 rounded bg-cortex-primary-50 text-cortex-primary-700 border border-cortex-primary-200">
                {{ gate }}
              </span>
            </div>
            <h1 class="text-xl font-bold text-cortex-text-primary mt-1 tracking-tight">
              {{ title }}
            </h1>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <RouterLink
            to="/app/cortex-operations"
            class="px-3 py-1.5 rounded-lg border border-cortex-border bg-cortex-surface text-xs font-medium text-cortex-text-secondary hover:bg-cortex-surface-subtle transition-colors"
          >
            ← Cockpit Opérations
          </RouterLink>
        </div>
      </div>

      <!-- Metadata Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div class="p-3 rounded-xl bg-cortex-surface-subtle border border-cortex-border space-y-1">
          <span class="text-[10px] uppercase font-bold text-cortex-text-muted">Route Canonique</span>
          <div class="font-mono font-semibold text-cortex-primary-800 text-xs truncate">
            {{ routePath }}
          </div>
        </div>

        <div class="p-3 rounded-xl bg-cortex-surface-subtle border border-cortex-border space-y-1">
          <span class="text-[10px] uppercase font-bold text-cortex-text-muted">Rôle & Responsabilité</span>
          <div class="font-semibold text-cortex-text-primary">
            {{ primaryRole }}
          </div>
        </div>

        <div class="p-3 rounded-xl bg-cortex-surface-subtle border border-cortex-border space-y-1">
          <span class="text-[10px] uppercase font-bold text-cortex-text-muted">Permission Requise</span>
          <div class="font-mono text-cortex-text-secondary">
            {{ requiredPermission || 'Authentification Standard' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Description & Engineering Readiness Card -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 p-6 rounded-2xl border border-cortex-border bg-cortex-surface shadow-xs space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-bold text-cortex-text-primary uppercase tracking-wider">
            Spécifications de l'écran
          </h2>
          <span class="inline-flex items-center gap-1.5 text-xs text-cortex-primary-700 font-medium bg-cortex-primary-50 px-2.5 py-1 rounded-full">
            <span class="w-2 h-2 rounded-full bg-cortex-primary-500 animate-pulse"></span>
            Prêt pour implémentation (Gate 2–5)
          </span>
        </div>

        <p class="text-xs text-cortex-text-secondary leading-relaxed">
          {{ description }}
        </p>

        <!-- Feature Slots or Custom Preview -->
        <div class="mt-4 pt-4 border-t border-cortex-border">
          <slot>
            <div class="p-8 rounded-xl border border-dashed border-cortex-border bg-cortex-surface-subtle flex flex-col items-center justify-center text-center space-y-2">
              <Sparkles class="w-8 h-8 text-cortex-primary-500 opacity-60" />
              <p class="text-xs font-semibold text-cortex-text-primary">
                Composant métier interactif en attente de livraison
              </p>
              <p class="text-[11px] text-cortex-text-muted max-w-md">
                L'infrastructure de navigation, le typage des routes et le contexte multi-tenant sont validés.
              </p>
            </div>
          </slot>
        </div>
      </div>

      <!-- Side Information: Canonical AI States & Operational Rules -->
      <div class="p-6 rounded-2xl border border-cortex-border bg-cortex-surface shadow-xs space-y-4">
        <h3 class="text-xs font-bold text-cortex-text-primary uppercase tracking-wider">
          Garanties Métier Non Négociables
        </h3>

        <ul class="space-y-2 text-xs text-cortex-text-secondary">
          <li class="flex items-start gap-2">
            <CheckCircle class="w-4 h-4 text-cortex-primary-600 flex-shrink-0 mt-0.5" />
            <span>Multi-tenant étanche avec validation serveur <code class="font-mono text-[10px]">X-Company-ID</code></span>
          </li>
          <li class="flex items-start gap-2">
            <CheckCircle class="w-4 h-4 text-cortex-primary-600 flex-shrink-0 mt-0.5" />
            <span>Zéro <code class="font-mono text-[10px]">fetch</code> direct — mutations via <code class="font-mono text-[10px]">CortexApiClient</code></span>
          </li>
          <li class="flex items-start gap-2">
            <CheckCircle class="w-4 h-4 text-cortex-primary-600 flex-shrink-0 mt-0.5" />
            <span>Audit append-only immuable systématique</span>
          </li>
          <li class="flex items-start gap-2">
            <CheckCircle class="w-4 h-4 text-cortex-primary-600 flex-shrink-0 mt-0.5" />
            <span>Contrats de confidentialité <code class="font-mono text-[10px]">OwnerStatementSafe</code></span>
          </li>
        </ul>

        <div class="pt-4 border-t border-cortex-border">
          <span class="text-[10px] uppercase font-bold text-cortex-text-muted block mb-2">
            Raccourcis Globaux
          </span>
          <div class="flex items-center gap-2 text-xs">
            <span class="inline-flex items-center gap-1">
              <kbd class="px-1.5 py-0.5 rounded bg-cortex-surface-subtle border border-cortex-border font-mono text-[10px]">⌘K</kbd>
              Recherche
            </span>
            <span class="inline-flex items-center gap-1">
              <kbd class="px-1.5 py-0.5 rounded bg-cortex-surface-subtle border border-cortex-border font-mono text-[10px]">⌘J</kbd>
              Copilote
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Sparkles,
  CheckCircle,
  LayoutDashboard,
  CalendarRange,
  FileSpreadsheet,
  PlusCircle,
  FileText,
  LogOut,
  LogIn,
  ShieldCheck,
  Package,
  PackageSearch,
  Barcode,
  Layers,
  Users,
  Percent,
  FileCheck,
  Inbox,
  Activity,
  MessageSquareCode,
  Scale,
  ShieldAlert,
  UploadCloud,
  History
} from 'lucide-vue-next'

const props = defineProps<{
  screenId: number
  title: string
  routePath: string
  priority: 'P0' | 'P1' | 'P2'
  gate: string
  primaryRole: string
  description: string
  requiredPermission?: string
  iconName?: string
}>()

const priorityBadgeClass = computed(() => {
  switch (props.priority) {
    case 'P0':
      return 'bg-red-100 text-red-800 border border-red-200'
    case 'P1':
      return 'bg-blue-100 text-blue-800 border border-blue-200'
    case 'P2':
      return 'bg-purple-100 text-purple-800 border border-purple-200'
    default:
      return 'bg-cortex-surface-subtle text-cortex-text-primary'
  }
})

const iconMap: Record<string, unknown> = {
  LayoutDashboard,
  CalendarRange,
  FileSpreadsheet,
  PlusCircle,
  FileText,
  LogOut,
  LogIn,
  ShieldCheck,
  Package,
  PackageSearch,
  Barcode,
  Layers,
  Users,
  Percent,
  FileCheck,
  Inbox,
  Sparkles,
  Activity,
  MessageSquareCode,
  Scale,
  ShieldAlert,
  UploadCloud,
  History
}

const iconComponent = computed(() => {
  if (props.iconName && iconMap[props.iconName]) {
    return iconMap[props.iconName]
  }
  return Sparkles
})
</script>
