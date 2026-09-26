<template>
  <!-- Sanitized Markdown (marked + DOMPurify). Links to Cortex routes open in the app. -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="claude-prose" :class="{ 'claude-caret': streaming }" @click="onClick" v-html="html" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ROUTER_BASE } from '@/app/router/routes'
import { renderMarkdown } from '../markdown'

const props = withDefaults(defineProps<{ text: string; streaming?: boolean }>(), { streaming: false })
const router = useRouter()

const html = computed(() => renderMarkdown(props.text))

function onClick(event: MouseEvent) {
  const anchor = (event.target as HTMLElement).closest('a')
  const href = anchor?.getAttribute('href') ?? ''
  if (!href.startsWith('/')) return
  event.preventDefault()
  const base = ROUTER_BASE.replace(/\/$/, '')
  void router.push(href.startsWith(base + '/') ? href.slice(base.length) : href)
}
</script>
