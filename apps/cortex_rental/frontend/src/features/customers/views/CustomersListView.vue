<template>
  <ScreenPending :title="t('routes.customers_list')" detail="La liste des clients ERPNext avec leurs locations, soldes et assurance arrive avec le lot Clients & Consignation." />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import ScreenPending from '@/design-system/components/page/ScreenPending.vue'

const { t } = useI18n()
</script>
