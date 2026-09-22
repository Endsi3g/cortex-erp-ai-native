<script setup>
// Cortex Shell Layout — wraps each page content area.
// Native Frappe Desk manages the main workspace sidebar and top navigation.
// Inner content is displayed directly on the clean workspace canvas without
// nesting a secondary sidebar.
defineProps({
	activePage: { type: String, default: "" },
});
</script>

<template>
	<div class="cx-shell">
		<div class="cx-shell-body">
			<slot />
		</div>
	</div>
</template>

<style scoped>
.cx-shell {
	display: flex;
	width: 100%;
	min-height: calc(100vh - var(--navbar-height, 56px));
	background: #ffffff;
}

.cx-shell-body {
	flex: 1;
	min-width: 0;
	overflow-x: hidden;
	display: flex;
	flex-direction: column;
	padding: 0 1.5rem 2rem;
}
</style>
