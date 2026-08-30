<script setup>
defineProps({
	title: { type: String, default: "Cortex Copilot" },
	subtitle: { type: String, default: "" },
	detachHref: { type: String, default: "" },
	closable: { type: Boolean, default: true },
});
defineEmits(["close", "detach"]);
</script>

<template>
	<header class="cp-header">
		<div>
			<h2 class="cx-title-card" style="margin: 0">{{ title }}</h2>
			<p v-if="subtitle" class="cx-text-meta" style="margin: 2px 0 0">{{ subtitle }}</p>
		</div>
		<div class="cp-header-actions">
			<button
				v-if="detachHref"
				class="cx-btn"
				title="Ouvrir en page complète"
				aria-label="Ouvrir en page complète"
				@click="$emit('detach')"
			>
				↗
			</button>
			<button
				v-if="closable"
				class="cx-btn"
				title="Fermer (Échap)"
				aria-label="Fermer le panneau Cortex Copilot"
				@click="$emit('close')"
			>
				✕
			</button>
		</div>
	</header>
</template>

<style scoped>
.cp-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	padding: var(--space-3) var(--space-4);
	border-bottom: 1px solid var(--cortex-border);
}
.cp-header-actions {
	display: flex;
	gap: var(--space-1);
}
</style>
