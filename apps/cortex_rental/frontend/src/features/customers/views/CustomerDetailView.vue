<template>
  <ScreenPending :title="t('routes.customer_detail')" detail="La fiche client 360 arrive avec le lot Clients & Consignation." />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import ScreenPending from '@/design-system/components/page/ScreenPending.vue'

const { t } = useI18n()
</script>
