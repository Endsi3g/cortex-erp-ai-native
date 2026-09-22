<script setup>
// Cortex Operations System — Sidebar Navigation
//
// 64px icon-only sidebar, mounted inside the Vue page wrapper (inside
// .cortex-app, inside the Frappe Desk page content area).
// Navigation: frappe.set_route() — real Frappe page routing, not SPA
// history, so browser URL and Desk breadcrumbs stay correct.
//
// Active item highlighted by `activePage` prop — caller passes the
// current page key so the sidebar knows which item to mark active
// without reading frappe.get_route() on every render.
//
// Tooltip: native HTML `title` attribute — no dependency, no JS tooltip
// library needed for 8 items.

import { computed } from "vue";
import { ICONS } from "./CortexIcons.js";

const props = defineProps({
	activePage: { type: String, default: "" },
});

const NAV_ITEMS = [
	{
		key: "operations",
		label: "Opérations",
		icon: "grid",
		route: "cortex-operations",
	},
	{
		key: "availability",
		label: "Disponibilité",
		icon: "calendarRange",
		route: "cortex-availability",
	},
	{
		key: "rentals",
		label: "Locations",
		icon: "fileText",
		route: "cortex-rentals",
	},
	{
		key: "composer",
		label: "Nouveau devis",
		icon: "plusCircle",
		route: "cortex-rental/new",
	},
	{
		key: "checkin",
		label: "Retour Check-in",
		icon: "scanLine",
		route: "cortex-checkin",
	},
	{
		key: "consignment",
		label: "Consignation",
		icon: "packageIcon",
		route: "cortex-consignment",
	},
	{
		key: "approvals",
		label: "Approbations",
		icon: "shield",
		route: "cortex-approvals",
	},
	{
		key: "pnl",
		label: "Comptabilité",
		icon: "barChart3",
		route: "cortex-accounting-pnl",
	},
];

const userInitials = computed(() => {
	if (typeof frappe === "undefined") return "C";
	const full = frappe.session && (frappe.session.full_name || frappe.session.user || "");
	if (!full) return "C";
	return full
		.split(/\s+/)
		.slice(0, 2)
		.map((w) => w[0])
		.join("")
		.toUpperCase();
});

function navigate(route) {
	if (typeof frappe !== "undefined" && frappe.set_route) {
		frappe.set_route(route);
	}
}
</script>

<template>
	<aside class="cx-sidebar" role="navigation" aria-label="Navigation Cortex">
		<!-- Logo -->
		<div class="cx-sidebar-logo" aria-hidden="true">
			<span class="cx-sidebar-logo-mark">C</span>
		</div>

		<!-- Main navigation items -->
		<nav class="cx-sidebar-nav">
			<button
				v-for="item in NAV_ITEMS"
				:key="item.key"
				type="button"
				class="cx-sidebar-item"
				:class="{ 'cx-sidebar-item--active': activePage === item.key }"
				:title="item.label"
				:aria-label="item.label"
				:aria-current="activePage === item.key ? 'page' : undefined"
				@click="navigate(item.route)"
			>
				<span class="cx-sidebar-icon" v-html="ICONS[item.icon] || ICONS.packageIcon" aria-hidden="true" />
			</button>
		</nav>

		<!-- Bottom: settings + user avatar -->
		<div class="cx-sidebar-bottom">
			<button
				type="button"
				class="cx-sidebar-item"
				:class="{ 'cx-sidebar-item--active': activePage === 'settings' }"
				title="Paramètres"
				aria-label="Paramètres"
				@click="navigate('cortex-team')"
			>
				<span class="cx-sidebar-icon" v-html="ICONS.settings" aria-hidden="true" />
			</button>

			<button
				type="button"
				class="cx-sidebar-avatar"
				title="Profil utilisateur"
				aria-label="Profil utilisateur"
				@click="navigate('Form/User/me')"
			>
				{{ userInitials }}
			</button>
		</div>
	</aside>
</template>

<style scoped>
.cx-sidebar {
	width: 48px;
	flex-shrink: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	background: var(--cortex-surface);
	border-right: 1px solid var(--cortex-border);
	padding: var(--space-2) 0;
	min-height: 100%;
}

.cx-sidebar-logo {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border-radius: var(--radius-md);
	background: var(--cortex-emerald-600);
	margin-bottom: var(--space-3);
	flex-shrink: 0;
}

.cx-sidebar-logo-mark {
	font-size: 14px;
	font-weight: 700;
	color: #ffffff;
	line-height: 1;
	font-family: var(--font-sans);
}

.cx-sidebar-nav {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: var(--space-1);
	flex: 1;
}

.cx-sidebar-item {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 36px;
	height: 36px;
	border: none;
	border-radius: var(--radius-md);
	background: transparent;
	color: var(--cortex-text-muted);
	cursor: pointer;
	transition: background var(--motion-fast), color var(--motion-fast);
	padding: 0;
	flex-shrink: 0;
}

.cx-sidebar-item:hover {
	background: var(--cortex-surface-hover);
	color: var(--cortex-text-secondary);
}

.cx-sidebar-item--active {
	background: var(--cortex-emerald-50);
	color: var(--cortex-emerald-700);
	box-shadow: inset 2px 0 0 var(--cortex-emerald-600);
}

.cx-sidebar-item--active:hover {
	background: var(--cortex-emerald-100);
	color: var(--cortex-emerald-700);
}

.cx-sidebar-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 16px;
	height: 16px;
}

.cx-sidebar-bottom {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: var(--space-1);
	padding-top: var(--space-2);
	border-top: 1px solid var(--cortex-border);
	width: 100%;
	padding-left: 0;
}

.cx-sidebar-avatar {
	width: 32px;
	height: 32px;
	border-radius: 50%;
	background: var(--cortex-emerald-100);
	color: var(--cortex-emerald-800);
	font-size: 11px;
	font-weight: 700;
	font-family: var(--font-sans);
	border: none;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: background var(--motion-fast);
	margin-top: var(--space-1);
}

.cx-sidebar-avatar:hover {
	background: var(--cortex-emerald-200);
}

@media (prefers-reduced-motion: reduce) {
	.cx-sidebar-item,
	.cx-sidebar-avatar {
		transition: none;
	}
}
</style>
