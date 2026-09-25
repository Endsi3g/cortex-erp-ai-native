<template>
  <ScreenPending :title="t('routes.finance_invoices')" detail="Les factures d’acompte et de solde ERPNext liées aux locations arrivent avec le lot Finance." />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import ScreenPending from '@/design-system/components/page/ScreenPending.vue'

const { t } = useI18n()
</script>
