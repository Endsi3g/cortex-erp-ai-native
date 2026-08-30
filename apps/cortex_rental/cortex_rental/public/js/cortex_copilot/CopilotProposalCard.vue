<script setup>
defineProps({
	block: { type: Object, required: true }, // {title, summary, impact, action, draft_id, requires_approval}
});
const emit = defineEmits(["continue"]);

// Real follow-through for this proposal doesn't exist yet — there is
// no Transaction Composer to open prefilled (that's a separate,
// not-yet-built screen). Rather than wire a button that pretends to
// create something, clicking here re-engages the real chat pipeline
// with the proposal's own title as the next message — an honest
// "continue this" action instead of a fabricated mutation. Once the
// Composer exists, this same emit is what would open it instead.
function onPrimary() {
	emit("continue", block.title);
}
</script>

<template>
	<div class="cp-block cp-block-proposal">
		<div class="cp-block-head">
			<span class="cx-title-card">{{ block.title }}</span>
			<span v-if="block.requires_approval" class="cx-badge cp-approval-flag">approbation requise</span>
		</div>
		<p class="cx-text-body">{{ block.summary }}</p>
		<ul v-if="block.impact && block.impact.length" class="cp-impact-list">
			<li v-for="(line, i) in block.impact" :key="i" class="cx-text-meta">{{ line }}</li>
		</ul>
		<button class="cx-btn cx-btn-primary" @click="onPrimary">Continuer avec cette proposition</button>
	</div>
</template>

<style scoped>
.cp-block-proposal {
	background: var(--cortex-primary-50);
	border: 1px solid var(--cortex-primary-100);
	border-radius: var(--radius-md);
	padding: var(--space-3);
}
.cp-block-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-2);
	margin-bottom: var(--space-2);
}
.cp-approval-flag {
	background: var(--cortex-warning-50);
	color: var(--cortex-warning-700);
	border-color: var(--cortex-warning-500);
	font-size: 11px;
}
.cp-impact-list {
	margin: var(--space-2) 0;
	padding-left: 18px;
}
</style>
