<script setup>
import { computed } from "vue";

// items: [{ key, label, ready: boolean, hint?: string }]
const props = defineProps({
	title: { type: String, default: "" },
	items: { type: Array, required: true },
	blockedMessage: { type: String, default: "" },
});

const allReady = computed(() => props.items.every((i) => i.ready));
</script>

<template>
	<div class="cx-surface cx-readiness" style="padding: var(--space-4)">
		<div v-if="title" class="cx-text-label" style="margin-bottom: var(--space-3)">{{ title }}</div>
		<ul class="cx-readiness-list">
			<li v-for="item in items" :key="item.key" class="cx-readiness-item">
				<span
					class="cx-readiness-glyph"
					:style="{ color: item.ready ? 'var(--cortex-success-600)' : 'var(--cortex-text-disabled)' }"
					aria-hidden="true"
				>
					{{ item.ready ? "✓" : "○" }}
				</span>
				<span class="cx-text-body">
					{{ item.label }}
					<span v-if="!item.ready && item.hint" class="cx-text-meta"> — {{ item.hint }}</span>
				</span>
			</li>
		</ul>
		<p v-if="!allReady && blockedMessage" class="cx-readiness-blocked cx-text-critical">
			{{ blockedMessage }}
		</p>
	</div>
</template>

<style scoped>
.cx-readiness-list {
	list-style: none;
	margin: 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}
.cx-readiness-item {
	display: flex;
	align-items: flex-start;
	gap: var(--space-2);
}
.cx-readiness-glyph {
	font-weight: 700;
	flex-shrink: 0;
	width: 16px;
}
.cx-readiness-blocked {
	margin: var(--space-3) 0 0;
	padding: var(--space-2) var(--space-3);
	background: var(--cortex-warning-50);
	border: 1px solid var(--cortex-warning-500);
	border-radius: var(--radius-sm);
	font-size: 13px;
}
</style>
