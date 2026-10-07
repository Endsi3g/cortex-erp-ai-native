<script setup>
defineProps({
	block: { type: Object, required: true }, // {title, items, source_ids, checked_at}
});

// Heure de vérification lisible (« 6 oct. 2026, 16 h 58 ») plutôt que l'horodatage brut du serveur.
function checked(value) {
	const date = new Date(String(value || "").replace(" ", "T"));
	return Number.isNaN(date.getTime()) ? value : date.toLocaleString("fr-CA", { dateStyle: "medium", timeStyle: "short" });
}
</script>

<template>
	<section class="cp-fact" :aria-label="block.title">
		<h3 class="cp-fact-title">{{ block.title }}</h3>
		<ul class="cp-fact-list">
			<li v-for="(item, i) in block.items" :key="i">{{ item }}</li>
		</ul>
		<p v-if="block.checked_at || (block.source_ids && block.source_ids.length)" class="cp-fact-meta">
			<span v-if="block.checked_at">Données vérifiées le {{ checked(block.checked_at) }}</span>
			<details v-if="block.source_ids && block.source_ids.length" class="cp-sources">
				<summary>Sources ({{ block.source_ids.length }})</summary>
				<span class="cp-source-chips">
					<code v-for="id in block.source_ids" :key="id">{{ id }}</code>
				</span>
			</details>
		</p>
	</section>
</template>

<style scoped>
.cp-fact {
	margin: 0;
}
.cp-fact-title {
	margin: 0 0 6px;
	font-size: 14px;
	font-weight: 650;
	color: #0f172a;
}
.cp-fact-list {
	margin: 0;
	padding-left: 18px;
	font-size: 14.5px;
	line-height: 1.6;
	color: #1e293b;
}
.cp-fact-meta {
	display: flex;
	flex-wrap: wrap;
	align-items: baseline;
	gap: 4px 14px;
	margin: 8px 0 0;
	font-size: 12px;
	color: #64748b;
}
.cp-sources summary {
	cursor: pointer;
	list-style: none;
}
.cp-sources summary::-webkit-details-marker {
	display: none;
}
.cp-sources summary:hover {
	color: #0f172a;
	text-decoration: underline;
}
.cp-source-chips {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
	margin-top: 6px;
}
.cp-source-chips code {
	padding: 1px 6px;
	border-radius: 5px;
	background: #f1f5f9;
	font-size: 11px;
	color: #475569;
}
</style>
