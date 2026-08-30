<script setup>
// Grammar from docs/design-system.md "Structure de chaque écran":
// [Titre] [compteur/statut] / sous-titre / actions secondaires .. action primaire
defineProps({
	title: { type: String, required: true },
	subtitle: { type: String, default: "" },
});
</script>

<template>
	<header class="cx-page-header">
		<div class="cx-page-header-text">
			<h1 class="cx-title-page">
				{{ title }}
				<slot name="status" />
			</h1>
			<p v-if="subtitle" class="cx-text-meta" style="margin: 2px 0 0">{{ subtitle }}</p>
		</div>
		<div class="cx-page-header-actions">
			<div class="cx-flex cx-gap-2">
				<slot name="secondary" />
			</div>
			<div>
				<slot name="primary" />
			</div>
		</div>
	</header>
</template>

<style scoped>
.cx-page-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: var(--space-4);
	padding: var(--space-4) 0;
	flex-wrap: wrap;
}
.cx-page-header-actions {
	display: flex;
	align-items: center;
	gap: var(--space-4);
	flex-wrap: wrap;
}
</style>
