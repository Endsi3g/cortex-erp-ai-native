<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
import CopilotConversation from "../cortex_copilot/CopilotConversation.vue";
import { sendMessage, getMessages, listSessions, resolveDeskContext } from "../cortex_copilot/chatClient.js";
import { ICONS } from "../cortex_shared/CortexIcons.js";

// Suggestions : des phrases que la personne peut envoyer, jamais des réponses ou des chiffres inventés.
const PROMPTS = [
	{ roles: [], text: "Que dois-je traiter en priorité aujourd'hui ?" },
	{
		roles: ["Cortex Operations Manager", "Cortex Counter Staff", "Rental Manager", "Rental Operator"],
		text: "Quels équipements sont disponibles vendredi et samedi ?",
	},
	{
		roles: ["Cortex Operations Manager", "Cortex Counter Staff", "Rental Manager", "Rental Operator"],
		text: "Prépare un brouillon de location pour un client",
	},
	{ roles: ["Cortex Inventory Manager"], text: "Quels équipements sont en quarantaine ou endommagés ?" },
	{ roles: ["Cortex Finance Manager"], text: "Résume les factures de location à suivre" },
	{ roles: ["Cortex Consignment Manager"], text: "Prépare le relevé de consignation du mois" },
	{ roles: ["Cortex Account Reviewer"], text: "Quelles approbations attendent ma décision ?" },
];

// Raccourcis vers les espaces de travail Desk (routes = titres d'espaces épurés).
const WORKSPACES = [
	{ route: "cortex-operations", label: "Opérations", hint: "Locations, départs, retours", icon: "calendarRange" },
	{ route: "cortex-warehouse", label: "Entrepôt", hint: "Sorties, retours, séries", icon: "scanLine" },
	{ route: "cortex-catalog", label: "Catalogue", hint: "Équipements et kits", icon: "packageIcon" },
	{ route: "cortex-finance", label: "Finance", hint: "Facturation et consignation", icon: "dollarSign" },
	{ route: "cortex-ai", label: "IA", hint: "Boîte d'entrée, approbations, audit", icon: "sparkles" },
	{ route: "cortex-admin", label: "Administration", hint: "Règles, équipe, imports", icon: "settings" },
];

const CHIPS = [
	{ label: "Nouvelle location", route: ["Form", "Cortex Rental Transaction", "new"], icon: "plusCircle" },
	{ label: "Disponibilité du parc", route: ["query-report", "Disponibilité du parc"], icon: "calendar" },
	{ label: "Approbations", route: ["List", "Approval Request"], icon: "checkCircle" },
];

const messages = ref([]);
const sending = ref(false);
const chatSessionId = ref(null);
const text = ref("");
const sessions = ref([]);
const sessionsError = ref("");
const inputRef = ref(null);
const endRef = ref(null);
let nextId = 1;

const inConversation = computed(() => messages.value.length > 0 || sending.value);
const firstName = computed(() => {
	try {
		return frappe.user.first_name() || "";
	} catch (e) {
		return "";
	}
});
const greeting = computed(() => (firstName.value ? `Bonjour ${firstName.value}` : "Bonjour"));
const setupPending = computed(() => !!(frappe.boot.cortex_home && frappe.boot.cortex_home.setup_pending));
const prompts = computed(() => {
	const roles = frappe.user_roles || [];
	return PROMPTS.filter((p) => !p.roles.length || p.roles.some((r) => roles.includes(r))).slice(0, 4);
});

function go(route) {
	frappe.set_route(route);
}

function icon(name) {
	return ICONS[name] || "";
}

function resize() {
	const el = inputRef.value;
	if (!el) return;
	el.style.height = "auto";
	el.style.height = Math.min(el.scrollHeight, 220) + "px";
}

function scrollToEnd() {
	nextTick(() => {
		if (endRef.value) endRef.value.scrollIntoView({ behavior: "smooth", block: "end" });
	});
}

function push(msg) {
	messages.value.push({ id: nextId++, ...msg });
}

async function submit(value) {
	const message = (value !== undefined ? value : text.value).trim();
	if (!message || sending.value) return;
	text.value = "";
	nextTick(resize);
	push({ role: "user", text: message });
	sending.value = true;
	scrollToEnd();
	try {
		const response = await sendMessage(message, resolveDeskContext(), chatSessionId.value);
		chatSessionId.value = response.chat_session_id || chatSessionId.value;
		push({ role: "assistant", blocks: response.blocks || [] });
	} catch (err) {
		push({
			role: "assistant",
			blocks: [{ type: "error", title: "Cortex ne peut pas répondre", safe_message: err.message, retry_allowed: true }],
		});
	} finally {
		sending.value = false;
		scrollToEnd();
		nextTick(() => inputRef.value && inputRef.value.focus());
	}
}

function retry() {
	const last = [...messages.value].reverse().find((m) => m.role === "user");
	if (last) submit(last.text);
}

function onKeydown(e) {
	if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
		e.preventDefault();
		submit();
	}
}

async function openSession(name) {
	if (sending.value) return;
	sending.value = true;
	try {
		const response = await getMessages(name);
		const rows = response.data || [];
		messages.value = rows.map((row) => ({ id: nextId++, role: row.role, text: row.text, blocks: row.blocks || [] }));
		chatSessionId.value = name;
		scrollToEnd();
	} catch (err) {
		frappe.show_alert({ message: err.message, indicator: "red" }, 6);
	} finally {
		sending.value = false;
	}
}

function newConversation() {
	messages.value = [];
	chatSessionId.value = null;
	nextTick(() => inputRef.value && inputRef.value.focus());
}

function sessionLabel(session) {
	const when = session.last_message_at || session.started_at;
	if (!when) return "Conversation";
	try {
		return "Conversation du " + frappe.datetime.str_to_user(when.slice(0, 16));
	} catch (e) {
		return "Conversation";
	}
}

async function refresh() {
	try {
		const response = await listSessions();
		sessions.value = (response.data || []).slice(0, 5);
		sessionsError.value = "";
	} catch (err) {
		sessions.value = [];
		sessionsError.value = err.message;
	}
}

onMounted(() => {
	refresh();
	nextTick(() => inputRef.value && inputRef.value.focus());
});

defineExpose({ refresh });
</script>

<template>
	<div class="cortex-home cortex-app" :class="{ 'is-chat': inConversation }">
		<section class="ch-stage">
			<Transition name="ch-fade" mode="out-in">
				<header v-if="!inConversation" key="hero" class="ch-hero">
					<span class="ch-mark" aria-hidden="true" v-html="icon('sparkles')"></span>
					<p class="ch-greeting">{{ greeting }}</p>
					<h1 class="ch-title">Que puis-je faire pour vous ?</h1>
				</header>

				<div v-else key="chat" class="ch-thread">
					<div class="ch-thread-bar">
						<button type="button" class="ch-link" @click="newConversation">
							<span aria-hidden="true" v-html="icon('plusCircle')"></span> Nouvelle conversation
						</button>
					</div>
					<CopilotConversation :messages="messages" :sending="sending" @continue="submit" @retry="retry" />
					<div ref="endRef"></div>
				</div>
			</Transition>

			<form class="ch-composer" @submit.prevent="submit()">
				<label class="ch-sr" for="cortex-home-input">Message pour Cortex</label>
				<textarea
					id="cortex-home-input"
					ref="inputRef"
					v-model="text"
					class="ch-input"
					rows="1"
					placeholder="Demandez à Cortex…"
					:disabled="sending"
					@input="resize"
					@keydown="onKeydown"
				></textarea>
				<div class="ch-composer-row">
					<p class="ch-hint">
						Cortex prépare des brouillons et des demandes. Contrats, factures et envois exigent une validation
						humaine. Entrée pour envoyer, Maj+Entrée pour un saut de ligne.
					</p>
					<button type="submit" class="ch-send" :disabled="sending || !text.trim()" aria-label="Envoyer">
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
					</button>
				</div>
			</form>

			<Transition name="ch-fade">
				<div v-if="!inConversation" class="ch-below">
					<ul class="ch-chips" aria-label="Raccourcis">
						<li v-for="chip in CHIPS" :key="chip.label">
							<button type="button" class="ch-chip" @click="go(chip.route)">
								<span aria-hidden="true" v-html="icon(chip.icon)"></span>{{ chip.label }}
							</button>
						</li>
					</ul>

					<div v-if="setupPending" class="ch-setup" role="status">
						<div>
							<strong>Terminez la mise en route de votre entreprise.</strong>
							<span>Profil, équipe et catalogue : quelques étapes guidées dans l'espace Cortex.</span>
						</div>
						<button type="button" class="ch-chip ch-chip-accent" @click="go('cortex-rental')">Continuer</button>
					</div>

					<h2 class="ch-section">Essayez de demander</h2>
					<ul class="ch-prompts">
						<li v-for="(prompt, i) in prompts" :key="prompt.text" :style="{ '--i': i }">
							<button type="button" class="ch-prompt" @click="submit(prompt.text)">{{ prompt.text }}</button>
						</li>
					</ul>

					<h2 class="ch-section">Espaces de travail</h2>
					<ul class="ch-tiles">
						<li v-for="(tile, i) in WORKSPACES" :key="tile.route" :style="{ '--i': i }">
							<a class="ch-tile" :href="`/app/${tile.route}`" @click.prevent="go(tile.route)">
								<span class="ch-tile-icon" aria-hidden="true" v-html="icon(tile.icon)"></span>
								<span class="ch-tile-text"><strong>{{ tile.label }}</strong><small>{{ tile.hint }}</small></span>
							</a>
						</li>
					</ul>

					<template v-if="sessions.length">
						<h2 class="ch-section">Conversations récentes</h2>
						<ul class="ch-recent">
							<li v-for="session in sessions" :key="session.name">
								<button type="button" class="ch-recent-item" @click="openSession(session.name)">
									<span aria-hidden="true" v-html="icon('clock')"></span>{{ sessionLabel(session) }}
								</button>
							</li>
						</ul>
					</template>
					<p v-else-if="sessionsError" class="ch-note">{{ sessionsError }}</p>
				</div>
			</Transition>
		</section>
	</div>
</template>
