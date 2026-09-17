<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import { ICONS } from "./CortexIcons.js";

const isOpen = ref(false);
const query = ref("");
const selectedIndex = ref(0);
const inputRef = ref(null);

const emit = defineEmits(["execute-action", "navigate"]);

// Items de démonstration et commandes réelles
const ALL_ITEMS = [
	// Navigation Pages
	{ id: "nav-avail", type: "page", title: "Calendrier de Disponibilité & Flotte", icon: "calendar", route: "cortex-availability", shortcut: "G D" },
	{ id: "nav-composer", type: "page", title: "Nouveau Devis & Réservation", icon: "fileText", route: "cortex-composer", shortcut: "G N" },
	{ id: "nav-checkin", type: "page", title: "Scanner & Retours Atelier", icon: "barcode", route: "cortex-checkin", shortcut: "G C" },
	{ id: "nav-pnl", type: "page", title: "P&L Analytique & Finances", icon: "sparkles", route: "cortex-accounting-pnl", shortcut: "G P" },
	{ id: "nav-fleet", type: "page", title: "Parc Matériel & Maintenance", icon: "camera", route: "cortex-fleet", shortcut: "G F" },
	{ id: "nav-customers", type: "page", title: "Clients & Risque Assurance", icon: "shield", route: "cortex-customers", shortcut: "G U" },
	{ id: "nav-supervision", type: "page", title: "Supervision IA & Approbations", icon: "alert", route: "cortex-supervision", shortcut: "G S" },

	// Actions Magiques IA
	{ id: "ai-conflict", type: "ai", title: "Résoudre les conflits de disponibilité par équivalence IA", icon: "sparkles", action: "resolve_conflicts" },
	{ id: "ai-dune", type: "ai", title: "Générer un devis automatique pour « Dune 3 Productions »", icon: "sparkles", action: "quote_dune" },
	{ id: "ai-insurance", type: "ai", title: "Auditer la validité des attestations d'assurance du mois", icon: "shield", action: "audit_insurance" },
	{ id: "ai-maintenance", type: "ai", title: "Calculer les alertes d'usure préventive des capteurs caméras", icon: "camera", action: "calc_maintenance" },

	// Équipements de référence
	{ id: "eq-alx", type: "equipment", title: "ARRI Alexa 35 (SN-ALX-001, SN-ALX-002, SN-ALX-003)", icon: "camera", route: "cortex-fleet?item=ARRI-ALX35" },
	{ id: "eq-cke", type: "equipment", title: "Cooke S4/i Prime Set T2.0 (SN-CKE-001, SN-CKE-002)", icon: "lens", route: "cortex-fleet?item=COOKE-S4I-SET" },
	{ id: "eq-apt", type: "equipment", title: "Aputure Electro Storm 1200D Pro Daylight", icon: "package", route: "cortex-fleet?item=APUTURE-1200D" },

	// Clients
	{ id: "cli-dune", type: "customer", title: "Dune 3 Productions Inc. — Compte VIP (Risque Faible)", icon: "shield", route: "cortex-customers?client=dune" },
	{ id: "cli-hbo", type: "customer", title: "HBO Series Montreal — Assurance validée (3 500 000 $)", icon: "shield", route: "cortex-customers?client=hbo" },
];

const filteredItems = computed(() => {
	const q = query.value.trim().toLowerCase();
	if (!q) return ALL_ITEMS;
	return ALL_ITEMS.filter((item) => {
		return item.title.toLowerCase().includes(q) || item.type.toLowerCase().includes(q);
	});
});

function open() {
	isOpen.value = true;
	query.value = "";
	selectedIndex.value = 0;
	nextTick(() => {
		if (inputRef.value) inputRef.value.focus();
	});
}

function close() {
	isOpen.value = false;
	query.value = "";
}

function selectItem(index) {
	const item = filteredItems.value[index];
	if (!item) return;

	if (item.type === "page" || item.type === "equipment" || item.type === "customer") {
		if (typeof frappe !== "undefined" && frappe.set_route) {
			frappe.set_route(item.route);
		}
		emit("navigate", item);
	} else if (item.type === "ai") {
		emit("execute-action", item);
	}
	close();
}

function onKeydown(e) {
	// Raccourci Cmd+K / Ctrl+K
	if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
		e.preventDefault();
		if (isOpen.value) close();
		else open();
		return;
	}

	if (!isOpen.value) return;

	if (e.key === "Escape") {
		close();
	} else if (e.key === "ArrowDown") {
		e.preventDefault();
		selectedIndex.value = (selectedIndex.value + 1) % filteredItems.value.length;
	} else if (e.key === "ArrowUp") {
		e.preventDefault();
		selectedIndex.value =
			(selectedIndex.value - 1 + filteredItems.value.length) % filteredItems.value.length;
	} else if (e.key === "Enter") {
		e.preventDefault();
		selectItem(selectedIndex.value);
	}
}

onMounted(() => {
	window.addEventListener("keydown", onKeydown);
});

onBeforeUnmount(() => {
	window.removeEventListener("keydown", onKeydown);
});

defineExpose({ open, close });
</script>

<template>
	<Teleport to="body">
		<transition name="cx-cmd-fade">
			<div v-if="isOpen" class="cx-cmd-overlay" @click.self="close">
				<div class="cx-cmd-dialog" role="dialog" aria-modal="true" aria-label="Recherche et commandes rapides">
					<div class="cx-cmd-header">
						<span class="cx-cmd-search-icon" v-html="ICONS.sparkles"></span>
						<input
							ref="inputRef"
							v-model="query"
							type="text"
							class="cx-cmd-input"
							placeholder="Rechercher équipement, client, ou demander une action IA…"
							aria-label="Champ de commande"
						/>
						<span class="cx-cmd-esc-badge" @click="close">Échap</span>
					</div>

					<div class="cx-cmd-list" role="listbox">
						<div
							v-for="(item, idx) in filteredItems"
							:key="item.id"
							class="cx-cmd-item"
							:class="{ 'is-selected': idx === selectedIndex }"
							role="option"
							:aria-selected="idx === selectedIndex"
							@click="selectItem(idx)"
							@mouseenter="selectedIndex = idx"
						>
							<div class="cx-cmd-item-left">
								<span class="cx-cmd-item-icon" :class="item.type" v-html="ICONS[item.icon] || ICONS.package"></span>
								<span class="cx-cmd-item-title">{{ item.title }}</span>
							</div>

							<div class="cx-cmd-item-right">
								<span v-if="item.type === 'ai'" class="cx-badge cx-badge-success">Action IA</span>
								<span v-else-if="item.type === 'equipment'" class="cx-badge cx-badge-neutral">Matériel</span>
								<span v-else-if="item.type === 'customer'" class="cx-badge cx-badge-info">Client</span>
								<span v-if="item.shortcut" class="cx-cmd-kbd">{{ item.shortcut }}</span>
								<span class="cx-cmd-enter-hint" v-if="idx === selectedIndex">↵</span>
							</div>
						</div>

						<div v-if="filteredItems.length === 0" class="cx-cmd-empty">
							Aucun résultat pour « {{ query }} ». Appuyez sur Entrée pour demander au Copilot.
						</div>
					</div>

					<footer class="cx-cmd-footer">
						<div class="cx-cmd-footer-hints">
							<span><kbd class="cx-kbd">↑</kbd> <kbd class="cx-kbd">↓</kbd> Naviguer</span>
							<span><kbd class="cx-kbd">↵</kbd> Sélectionner</span>
							<span><kbd class="cx-kbd">⌘J</kbd> Ouvrir Copilot</span>
						</div>
						<span class="cx-cmd-brand">Cortex Native AI</span>
					</footer>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<style scoped>
.cx-cmd-overlay {
	position: fixed;
	inset: 0;
	background: rgba(15, 23, 42, 0.45);
	backdrop-filter: blur(4px);
	z-index: 1000;
	display: flex;
	align-items: flex-start;
	justify-content: center;
	padding-top: 12vh;
}

.cx-cmd-dialog {
	width: 640px;
	max-width: 90vw;
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
	box-shadow: 0 16px 48px rgba(0, 0, 0, 0.16);
	overflow: hidden;
	animation: cmdZoom 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes cmdZoom {
	from {
		opacity: 0;
		transform: scale(0.97);
	}
	to {
		opacity: 1;
		transform: scale(1);
	}
}

.cx-cmd-header {
	display: flex;
	align-items: center;
	padding: var(--space-3) var(--space-4);
	border-bottom: 1px solid var(--cortex-border);
	gap: var(--space-3);
}

.cx-cmd-search-icon {
	color: var(--cortex-primary-600);
	display: flex;
	align-items: center;
	flex-shrink: 0;
}

.cx-cmd-input {
	flex: 1;
	border: none;
	background: transparent;
	font-size: 14.5px;
	color: var(--cortex-text-primary);
	outline: none;
	font-family: inherit;
}
.cx-cmd-input::placeholder {
	color: var(--cortex-text-muted);
}

.cx-cmd-esc-badge {
	font-size: 11px;
	padding: 2px 6px;
	background: var(--cortex-surface-muted);
	border: 1px solid var(--cortex-border);
	border-radius: 4px;
	color: var(--cortex-text-muted);
	cursor: pointer;
}

.cx-cmd-list {
	max-height: 380px;
	overflow-y: auto;
	padding: var(--space-2);
}

.cx-cmd-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 9px var(--space-3);
	border-radius: var(--radius-md);
	cursor: pointer;
	transition: background 0.1s ease;
}

.cx-cmd-item.is-selected {
	background: var(--cortex-surface-muted);
}

.cx-cmd-item-left {
	display: flex;
	align-items: center;
	gap: var(--space-3);
	flex: 1;
	overflow: hidden;
}

.cx-cmd-item-icon {
	display: flex;
	align-items: center;
	color: var(--cortex-text-muted);
	flex-shrink: 0;
}
.cx-cmd-item-icon.ai {
	color: var(--cortex-primary-600);
}

.cx-cmd-item-title {
	font-size: 13px;
	color: var(--cortex-text-primary);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.cx-cmd-item-right {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	flex-shrink: 0;
}

.cx-cmd-kbd {
	font-size: 10.5px;
	font-family: var(--font-mono);
	color: var(--cortex-text-muted);
}

.cx-cmd-enter-hint {
	font-size: 12px;
	color: var(--cortex-text-muted);
	font-family: var(--font-mono);
}

.cx-cmd-empty {
	padding: var(--space-6) var(--space-4);
	text-align: center;
	font-size: 13px;
	color: var(--cortex-text-muted);
}

.cx-cmd-footer {
	padding: var(--space-2) var(--space-4);
	border-top: 1px solid var(--cortex-border);
	background: var(--cortex-surface-muted);
	display: flex;
	align-items: center;
	justify-content: space-between;
	font-size: 11px;
	color: var(--cortex-text-muted);
}

.cx-cmd-footer-hints {
	display: flex;
	gap: var(--space-3);
}

.cx-kbd {
	display: inline-block;
	padding: 1px 4px;
	font-size: 10px;
	font-family: var(--font-mono);
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	border-radius: 3px;
}

.cx-cmd-brand {
	font-weight: 500;
	color: var(--cortex-primary-600);
}

/* Transitions */
.cx-cmd-fade-enter-active,
.cx-cmd-fade-leave-active {
	transition: opacity 0.15s ease;
}
.cx-cmd-fade-enter-from,
.cx-cmd-fade-leave-to {
	opacity: 0;
}
</style>
