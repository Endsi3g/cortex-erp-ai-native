<script setup>
// Cortex Shell Layout — wraps each page with sidebar + optional topbar.
//
// Mounted INSIDE the Frappe Desk page content area (the Vue root div
// `.cortex-app`). The shell adds a left sidebar column within the page
// content, NOT outside the Frappe chrome. The sidebar overlays the Frappe
// Desk workspace nav only within this page's render area.
//
// Usage (in each page component):
//   <CortexShell active-page="pnl">
//     <!-- page content goes here -->
//   </CortexShell>
import CortexSidebar from "./CortexSidebar.vue";

defineProps({
	activePage: { type: String, default: "" },
});
</script>

<template>
	<div class="cx-shell">
		<CortexSidebar :active-page="activePage" />
		<div class="cx-shell-body">
			<slot />
		</div>
	</div>
</template>

<style scoped>
.cx-shell {
	display: flex;
	min-height: calc(100vh - var(--navbar-height, 56px));
	background: var(--cortex-canvas);
}

.cx-shell-body {
	flex: 1;
	min-width: 0;
	overflow-x: hidden;
	display: flex;
	flex-direction: column;
}
</style>
