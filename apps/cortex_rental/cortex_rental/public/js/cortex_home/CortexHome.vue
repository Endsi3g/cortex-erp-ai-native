<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, provide, watch } from "vue";
import CopilotConversation from "../cortex_copilot/CopilotConversation.vue";
import { sendMessage, getMessages, listSessions, resolveDeskContext, apiCall } from "../cortex_copilot/chatClient.js";

// Les trois cartes ouvrent un questionnaire guidé dans la conversation (interface déterministe, sans modèle d'IA).
const ACTION_CARDS = [
	{
		id: "quote",
		title: "Nouvelle location",
		desc: "Créer un devis : client, dates, équipement, prix",
		route: ["Form", "Cortex Rental Transaction", "new"],
		linkLabel: "Ouvrir le formulaire ERPNext",
		flow: "quote",
	},
	{
		id: "availability",
		title: "Grille de disponibilité",
		desc: "Voir ce qui est libre sur une période",
		route: ["cortex-availability"],
		linkLabel: "Ouvrir la grille complète",
		flow: "availability",
	},
	{
		id: "approvals",
		title: "Demandes d'approbation",
		desc: "Examiner et décider les demandes en attente",
		route: ["List", "Approval Request"],
		linkLabel: "Ouvrir la liste des approbations",
		flow: "approvals",
	},
];

// Les questionnaires, les propositions et l'état « IA réelle / Démonstration » sont propres à cette page.
provide("cortexFlows", true);

const BANNER_KEY = "cortex_home_demo_banner";
const messages = ref([]);
const sending = ref(false);
const chatSessionId = ref(null);
const text = ref("");
const sessions = ref([]);
const sessionsError = ref("");
const sessionsLoaded = ref(false);
const search = ref("");
const confirmDelete = ref("");
const showHistory = ref(false);
const showSettings = ref(false);
const showStatus = ref(false);
const confirmClear = ref(false);
const isListening = ref(false);
const inputRef = ref(null);
const searchRef = ref(null);
const endRef = ref(null);
const aiStatus = ref(null); // { mode: "ai" | "demo", provider, model } — lu côté serveur, jamais deviné ici
const bannerOn = ref(true);
let nextId = 1;
let speechRec = null;

const inConversation = computed(() => messages.value.length > 0 || sending.value);
const isDemo = computed(() => !aiStatus.value || aiStatus.value.mode === "demo");
const canConfigureAi = computed(() => {
	try {
		return ["System Manager", "Cortex System Manager"].some((role) => frappe.user.has_role(role));
	} catch (e) {
		return false;
	}
});

const displayName = computed(() => {
	// Prénom de la personne connectée, jamais un nom inventé : sans prénom connu, on salue sans nom.
	try {
		const full = (frappe.session && frappe.session.user_fullname) || "";
		const first = (frappe.user.first_name && frappe.user.first_name()) || "";
		for (const candidate of [first, full.split(" ")[0]]) {
			if (candidate && !["Administrator", "Guest", "Dev"].includes(candidate)) return candidate;
		}
	} catch (e) {}
	return "";
});

const greeting = computed(() => {
	const h = new Date().getHours();
	const moment = h < 12 ? "Bonjour" : h < 18 ? "Bon après-midi" : "Bonsoir";
	return displayName.value ? `${moment}, ${displayName.value}.` : `${moment}.`;
});

const canSend = computed(() => text.value.trim().length > 0 && !sending.value);

// ── Historique : groupes « Aujourd'hui », « Cette semaine », « Plus ancien », filtrés par la recherche ──
const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
function sessionDate(session) {
	const raw = session.last_message_at || session.started_at || "";
	const parsed = new Date(String(raw).replace(" ", "T"));
	return Number.isNaN(parsed.getTime()) ? null : parsed;
}
function sessionLabel(session) {
	if (session.title) return session.title;
	const when = sessionDate(session);
	return when ? "Conversation du " + when.toLocaleDateString("fr-CA", { day: "numeric", month: "long" }) : "Conversation";
}
function sessionWhen(session) {
	const when = sessionDate(session);
	if (!when) return "";
	const time = when.toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" });
	return startOfDay(when) === startOfDay(new Date()) ? time : when.toLocaleDateString("fr-CA", { day: "numeric", month: "short" }) + " · " + time;
}
const groupedSessions = computed(() => {
	const q = search.value.trim().toLowerCase();
	const today = startOfDay(new Date());
	const week = today - 6 * 86400000;
	const groups = [
		{ label: "Aujourd'hui", rows: [] },
		{ label: "Cette semaine", rows: [] },
		{ label: "Plus ancien", rows: [] },
	];
	for (const session of sessions.value) {
		if (q && !sessionLabel(session).toLowerCase().includes(q)) continue;
		const when = sessionDate(session);
		const day = when ? startOfDay(when) : 0;
		(day >= today ? groups[0] : day >= week ? groups[1] : groups[2]).rows.push(session);
	}
	return groups.filter((g) => g.rows.length);
});

function go(route) {
	frappe.set_route(route);
}

function resize() {
	const el = inputRef.value;
	if (!el) return;
	el.style.height = "auto";
	el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

function scrollToEnd() {
	nextTick(() => {
		if (endRef.value) endRef.value.scrollIntoView({ behavior: "smooth", block: "end" });
	});
}

function push(msg) {
	messages.value.push({ id: nextId++, ...msg });
}

function toggleVoice() {
	const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
	if (!SpeechRec) {
		frappe.show_alert({ message: "La saisie vocale n'est pas disponible dans ce navigateur.", indicator: "orange" }, 5);
		return;
	}
	if (isListening.value) {
		speechRec && speechRec.stop();
		isListening.value = false;
		return;
	}
	try {
		speechRec = new SpeechRec();
		speechRec.lang = "fr-CA";
		speechRec.continuous = false;
		speechRec.interimResults = false;
		speechRec.onstart = () => {
			isListening.value = true;
		};
		speechRec.onresult = (evt) => {
			const transcript = evt.results[0][0].transcript;
			text.value = text.value ? `${text.value} ${transcript}` : transcript;
			nextTick(resize);
		};
		speechRec.onerror = () => {
			isListening.value = false;
		};
		speechRec.onend = () => {
			isListening.value = false;
		};
		speechRec.start();
	} catch (e) {
		isListening.value = false;
	}
}

// Une carte lance son questionnaire dans la conversation ; rien n'est envoyé au modèle.
function startFlow(flow) {
	closePanels();
	push({ role: "assistant", flow });
	scrollToEnd();
}

function onFlow(flow) {
	startFlow(flow);
}

async function submit(value) {
	const message = (typeof value === "string" ? value : text.value).trim();
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
		refresh();
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
		showHistory.value = false;
		scrollToEnd();
	} catch (err) {
		frappe.show_alert({ message: err.message, indicator: "red" }, 6);
	} finally {
		sending.value = false;
	}
}

// Retour à l'écran d'accueil de l'assistant : l'historique du serveur n'est jamais touché.
function newConversation() {
	messages.value = [];
	chatSessionId.value = null;
	text.value = "";
	closePanels();
	nextTick(() => inputRef.value && inputRef.value.focus());
}

function closePanels() {
	showHistory.value = false;
	showSettings.value = false;
	showStatus.value = false;
	confirmClear.value = false;
	confirmDelete.value = "";
}

function toggleHistory() {
	const open = !showHistory.value;
	closePanels();
	showHistory.value = open;
	if (open) {
		refresh();
		nextTick(() => searchRef.value && searchRef.value.focus());
	}
}

function toggleSettings() {
	const open = !showSettings.value;
	closePanels();
	showSettings.value = open;
}

function toggleStatus() {
	const open = !showStatus.value;
	closePanels();
	showStatus.value = open;
}

function setBanner(value) {
	bannerOn.value = value;
	try {
		localStorage.setItem(BANNER_KEY, value ? "1" : "0");
	} catch (e) {}
}

async function removeSession(name) {
	try {
		await apiCall("cortex_rental.api.v1.chat.delete_session", { name }, "POST");
		if (chatSessionId.value === name) newConversation();
		confirmDelete.value = "";
		showHistory.value = true;
		await refresh();
	} catch (err) {
		frappe.show_alert({ message: err.message, indicator: "red" }, 6);
	}
}

async function clearHistory() {
	try {
		const result = await apiCall("cortex_rental.api.v1.chat.clear_history", {}, "POST");
		newConversation();
		await refresh();
		frappe.show_alert({ message: `${result.deleted || 0} conversation(s) retirée(s) de votre historique.`, indicator: "green" }, 5);
	} catch (err) {
		frappe.show_alert({ message: err.message, indicator: "red" }, 6);
	}
}

async function refresh() {
	try {
		const response = await listSessions();
		sessions.value = response.data || [];
		sessionsError.value = "";
	} catch (err) {
		sessions.value = [];
		sessionsError.value = err.message;
	} finally {
		sessionsLoaded.value = true;
	}
}

async function loadStatus() {
	try {
		aiStatus.value = await apiCall("cortex_rental.api.v1.chat.status", {});
	} catch (e) {
		aiStatus.value = null; // inconnu : on affiche « Démonstration » plutôt que de promettre une IA
	}
}

// Fil d'Ariane de la barre du haut (cortex_pages.js) : « Assistant IA › Conversation », « Assistant IA » ramène à l'accueil.
function publishState() {
	window.cortex_home_state = { inChat: inConversation.value };
	window.dispatchEvent(new CustomEvent("cortex-home:state"));
}
watch(inConversation, publishState);

const INSIDE = [".ch-pop", ".ch-top-btn", ".ch-status-wrap", ".ch-drawer"];
function onOutside(event) {
	// composedPath() garde le chemin même si le bouton cliqué vient d'être retiré de la page par Vue (ex. « Supprimer »).
	const path = event.composedPath ? event.composedPath() : [];
	const inside = path.some((node) => node.matches && INSIDE.some((selector) => node.matches(selector)));
	if (!inside) closePanels();
}
function onEscape(event) {
	if (event.key === "Escape") closePanels();
}

onMounted(() => {
	try {
		bannerOn.value = localStorage.getItem(BANNER_KEY) !== "0";
	} catch (e) {}
	refresh();
	loadStatus();
	publishState();
	window.addEventListener("cortex-home:reset", newConversation);
	document.addEventListener("click", onOutside);
	document.addEventListener("keydown", onEscape);
	nextTick(() => inputRef.value && inputRef.value.focus());
});

onBeforeUnmount(() => {
	window.removeEventListener("cortex-home:reset", newConversation);
	document.removeEventListener("click", onOutside);
	document.removeEventListener("keydown", onEscape);
});

defineExpose({ refresh });
</script>

<template>
	<div class="cortex-home cortex-app" :class="{ 'is-chat': inConversation }">
		<!-- ═══ ACTIONS EN HAUT À DROITE ═══ -->
		<header class="ch-top-actions" aria-label="Actions de l'assistant">
			<button type="button" class="ch-top-btn" title="Nouvelle conversation" aria-label="Nouvelle conversation" @click="newConversation">
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" /></svg>
			</button>
			<button type="button" class="ch-top-btn" :class="{ 'is-active': showHistory }" title="Historique des conversations" aria-label="Historique des conversations" :aria-expanded="showHistory" @click="toggleHistory">
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
			</button>
			<div class="ch-pop-wrap">
				<button type="button" class="ch-top-btn" :class="{ 'is-active': showSettings }" title="Réglages de l'assistant" aria-label="Réglages de l'assistant" :aria-expanded="showSettings" @click="toggleSettings">
					<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
				</button>
				<Transition name="ch-fade">
					<div v-if="showSettings" class="ch-pop ch-settings" role="dialog" aria-label="Réglages de l'assistant">
						<h2 class="ch-pop-title">Réglages de l'assistant</h2>
						<label class="ch-switch-row">
							<span>
								<strong>Bannière « Démonstration »</strong>
								<small>Affichée en haut de l'assistant tant qu'aucun modèle d'IA n'est configuré.</small>
							</span>
							<input type="checkbox" role="switch" :checked="bannerOn" @change="setBanner($event.target.checked)" />
						</label>
						<div class="ch-pop-row">
							<span>
								<strong>Mon historique</strong>
								<small>Retire vos conversations de la liste. Leurs messages restent au journal de la société (non modifiable) ; les devis et les demandes ne sont pas touchés.</small>
							</span>
							<button v-if="!confirmClear" type="button" class="ch-pop-btn danger" @click="confirmClear = true">Effacer…</button>
							<span v-else class="ch-confirm">
								<button type="button" class="ch-pop-btn danger fill" @click="clearHistory(); confirmClear = false">Oui, effacer</button>
								<button type="button" class="ch-pop-btn" @click="confirmClear = false">Annuler</button>
							</span>
						</div>
						<button v-if="canConfigureAi" type="button" class="ch-pop-link" @click="go(['Form', 'Cortex AI Settings']); closePanels()">Budget et modèle IA →</button>
					</div>
				</Transition>
			</div>
		</header>

		<section class="ch-stage">
			<p v-if="isDemo && bannerOn && aiStatus" class="ch-demo-banner" role="status">
				<span><strong>Mode démonstration.</strong> Aucun modèle d'IA n'est configuré : les réponses sont assemblées à partir de vos données réelles, sans rédaction par une IA. Les questionnaires guidés fonctionnent normalement.</span>
				<button type="button" class="ch-demo-hide" @click="setBanner(false)">Masquer</button>
			</p>

			<Transition name="ch-fade" mode="out-in">
				<header v-if="!inConversation" key="hero" class="ch-hero">
					<h1 class="ch-title">{{ greeting }}</h1>
					<p class="ch-subtitle">Comment puis-je vous aider aujourd'hui&nbsp;?</p>
				</header>

				<div v-else key="chat" class="ch-thread">
					<CopilotConversation :messages="messages" :sending="sending" @continue="submit" @retry="retry" @flow="onFlow" />
					<div ref="endRef"></div>
				</div>
			</Transition>

			<!-- ═══ SAISIE ═══ -->
			<form class="ch-composer" @submit.prevent="submit()">
				<label class="ch-sr" for="cortex-home-input">Message pour Cortex</label>
				<textarea
					id="cortex-home-input"
					ref="inputRef"
					v-model="text"
					class="ch-input"
					rows="1"
					placeholder="Que puis-je faire pour vous aujourd'hui ?"
					:disabled="sending"
					@input="resize"
					@keydown="onKeydown"
				></textarea>

				<div class="ch-toolbar">
					<!-- État réel du moteur : lu côté serveur (IA réelle ou démonstration), jamais supposé -->
					<div class="ch-status-wrap">
						<button
							type="button"
							class="ch-status"
							:class="isDemo ? 'is-demo' : 'is-ai'"
							:aria-expanded="showStatus"
							:title="isDemo ? 'Démonstration : aucun modèle d\'IA configuré' : 'IA réelle : les réponses sont rédigées par le modèle configuré'"
							@click="toggleStatus"
						>
							<span class="ch-status-dot" aria-hidden="true"></span>
							<span>{{ !aiStatus ? "Vérification…" : isDemo ? "Démonstration" : "IA réelle · Gemini" }}</span>
						</button>
						<Transition name="ch-fade">
							<div v-if="showStatus" class="ch-pop ch-status-pop" role="dialog" aria-label="État de l'assistant">
								<template v-if="isDemo">
									<strong>Démonstration</strong>
									<p>Aucun modèle d'IA n'est configuré pour cette société. Les réponses sont assemblées à partir de vos données réelles (catalogue, disponibilité, approbations) ; rien n'est rédigé par une IA.</p>
									<p>Les questionnaires guidés et les formulaires fonctionnent normalement.</p>
								</template>
								<template v-else>
									<strong>IA réelle · Gemini</strong>
									<p>Les réponses sont rédigées par le modèle configuré, à partir de vos données et avec vos droits. Rien n'est approuvé sans vous.</p>
								</template>
							</div>
						</Transition>
					</div>

					<div class="ch-toolbar-spacer"></div>

					<button type="button" class="ch-tool-btn ch-tool-mic" :class="{ 'is-listening': isListening }" :title="isListening ? 'Arrêter l\'écoute' : 'Activer la saisie vocale'" aria-label="Saisie vocale" :aria-pressed="isListening" @click="toggleVoice">
						<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" /></svg>
					</button>

					<button type="submit" class="ch-send" :disabled="!canSend" aria-label="Envoyer">
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" /></svg>
					</button>
				</div>
			</form>

			<!-- ═══ CARTES : questionnaires guidés ═══ -->
			<Transition name="ch-fade">
				<div v-if="!inConversation" class="ch-below">
					<div class="ch-divider">
						<div class="ch-divider-line"></div>
						<div class="ch-divider-badge">Questionnaires guidés</div>
					</div>

					<ul class="ch-cards-grid" aria-label="Questionnaires guidés">
						<li v-for="card in ACTION_CARDS" :key="card.id" class="ch-card" :class="`ch-card-${card.id}`">
							<button type="button" class="ch-card-main" @click="startFlow({ name: card.flow })">
								<span class="ch-card-header" aria-hidden="true">
									<span v-if="card.id === 'quote'" class="ch-mock-window ch-window-code">
										<span class="ch-window-dots"><span class="ch-dot ch-dot-red"></span><span class="ch-dot ch-dot-yellow"></span><span class="ch-dot ch-dot-green"></span></span>
										<span class="ch-code-lines">
											<span class="ch-code-row"><span class="ch-bar ch-bar-purple" style="width: 28px"></span><span class="ch-bar ch-bar-gray" style="width: 50px"></span></span>
											<span class="ch-code-row"><span class="ch-bar ch-bar-purple" style="width: 20px"></span><span class="ch-bar ch-bar-dark" style="width: 36px"></span></span>
											<span class="ch-code-row ch-indent"><span class="ch-bar ch-bar-purple" style="width: 32px"></span><span class="ch-bar ch-bar-gray" style="width: 22px"></span></span>
											<span class="ch-code-row ch-indent"><span class="ch-bar ch-bar-purple" style="width: 16px"></span></span>
											<span class="ch-code-row"><span class="ch-bar ch-bar-dark" style="width: 30px"></span></span>
										</span>
									</span>
									<span v-else-if="card.id === 'availability'" class="ch-mock-window ch-window-browser">
										<span class="ch-window-dots"><span class="ch-dot ch-dot-red"></span><span class="ch-dot ch-dot-yellow"></span><span class="ch-dot ch-dot-green"></span></span>
										<span class="ch-browser-content">
											<span class="ch-bar ch-bar-dark ch-bar-thick" style="width: 38px"></span>
											<span class="ch-dash-chips"><span class="ch-mini-pill"></span><span class="ch-mini-pill"></span><span class="ch-mini-pill"></span></span>
											<span class="ch-sub-line"></span>
											<span class="ch-bar ch-bar-slate" style="width: 82%"></span>
											<span class="ch-bar ch-bar-gray" style="width: 65%"></span>
											<span class="ch-bar ch-bar-gray" style="width: 75%"></span>
										</span>
									</span>
									<span v-else class="ch-mock-window ch-window-dialog">
										<span class="ch-dialog-top">
											<span class="ch-avatar-wrap"><span class="ch-avatar-circle"></span><span class="ch-status-dot-mini"></span></span>
											<span class="ch-close-x">✕</span>
										</span>
										<span class="ch-dialog-content">
											<span class="ch-bar ch-bar-slate" style="width: 68%"></span>
											<span class="ch-bar ch-bar-gray" style="width: 88%"></span>
											<span class="ch-bar ch-bar-gray" style="width: 48%"></span>
										</span>
									</span>
								</span>
								<span class="ch-card-body">
									<span class="ch-card-title">{{ card.title }}</span>
									<span class="ch-card-desc">{{ card.desc }}</span>
								</span>
							</button>
							<button type="button" class="ch-card-link-btn" :title="card.linkLabel" :aria-label="card.linkLabel" @click="go(card.route)">
								<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
							</button>
						</li>
					</ul>
				</div>
			</Transition>
		</section>

		<!-- ═══ HISTORIQUE : tiroir à droite ═══ -->
		<Transition name="ch-slide">
			<aside v-if="showHistory" class="ch-drawer" role="dialog" aria-label="Historique des conversations">
				<header class="ch-drawer-head">
					<h2>Historique</h2>
					<button type="button" class="ch-drawer-close" aria-label="Fermer l'historique" @click="showHistory = false">✕</button>
				</header>
				<input ref="searchRef" v-model="search" class="ch-drawer-search" type="search" placeholder="Rechercher une conversation…" aria-label="Rechercher une conversation" />
				<div class="ch-drawer-body">
					<p v-if="sessionsError" class="ch-drawer-empty">{{ sessionsError }}</p>
					<p v-else-if="!sessionsLoaded" class="ch-drawer-empty">Chargement…</p>
					<p v-else-if="!sessions.length" class="ch-drawer-empty">Aucune conversation pour le moment. Les questionnaires guidés ne sont pas conservés ici : seules vos questions à l'assistant le sont.</p>
					<p v-else-if="!groupedSessions.length" class="ch-drawer-empty">Aucune conversation ne correspond.</p>
					<section v-for="group in groupedSessions" :key="group.label" class="ch-drawer-group">
						<h3>{{ group.label }}</h3>
						<div v-for="session in group.rows" :key="session.name" class="ch-drawer-row" :class="{ current: session.name === chatSessionId }">
							<template v-if="confirmDelete !== session.name">
								<button type="button" class="ch-drawer-open" @click="openSession(session.name)">
									<span class="ch-drawer-label">{{ sessionLabel(session) }}</span>
									<span class="ch-drawer-when">{{ sessionWhen(session) }}</span>
								</button>
								<button type="button" class="ch-drawer-del" aria-label="Retirer cette conversation" title="Retirer de l'historique" @click="confirmDelete = session.name">
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6M14 11v6" /><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /></svg>
								</button>
							</template>
							<div v-else class="ch-drawer-confirm">
								<span>Retirer de l'historique ?</span>
								<button type="button" class="ch-pop-btn danger fill" @click="removeSession(session.name)">Retirer</button>
								<button type="button" class="ch-pop-btn" @click="confirmDelete = ''">Annuler</button>
							</div>
						</div>
					</section>
				</div>
			</aside>
		</Transition>
	</div>
</template>

<style scoped>
/* ═══════════════════════════════════════
   LAYOUT GLOBAL & CANVAS BLANC
═══════════════════════════════════════ */
.cortex-home {
	background-color: #ffffff;
	position: relative;
	min-height: calc(100vh - 56px);
	display: flex;
	justify-content: center;
	padding: 64px 24px 100px;
	box-sizing: border-box;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
	-webkit-font-smoothing: antialiased;
}

/* ═══════════════════════════════════════
   BOUTONS ACTION EN HAUT À DROITE
═══════════════════════════════════════ */
.ch-top-actions {
	position: absolute;
	top: 18px;
	right: 28px;
	display: flex;
	align-items: center;
	gap: 10px;
	z-index: 10;
}

.ch-top-btn {
	width: 36px;
	height: 36px;
	border-radius: 50%;
	background: #ffffff;
	border: 1px solid #e5e9f2;
	color: #64748b;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	padding: 0;
	transition: all 0.15s ease;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.ch-top-btn:hover {
	background: #f8fafc;
	border-color: #cbd5e1;
	color: #1e293b;
	box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.ch-top-btn.is-active {
	background: #eff6ff;
	border-color: #3b82f6;
	color: #2563eb;
}

/* ═══════════════════════════════════════
   SCÈNE CENTRALE
═══════════════════════════════════════ */
.ch-stage {
	width: 100%;
	max-width: 900px;
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.ch-sr {
	position: absolute;
	width: 1px;
	height: 1px;
	overflow: hidden;
	clip: rect(0 0 0 0);
	white-space: nowrap;
}

/* ═══════════════════════════════════════
   HERO (espacement accru, typographie raffinée)
═══════════════════════════════════════ */
.ch-hero {
	text-align: center;
	padding-top: clamp(28px, 8vh, 72px);
	padding-bottom: 12px;
	user-select: none;
}

.ch-title {
	margin: 0;
	font-size: clamp(32px, 4.6vw, 40px);
	line-height: 1.15;
	font-weight: 600;
	letter-spacing: -0.02em;
	color: #111827;
}

.ch-subtitle {
	margin: 8px 0 0;
	font-size: clamp(22px, 3.2vw, 30px);
	line-height: 1.25;
	font-weight: 500;
	color: #5b6b82;
	letter-spacing: -0.015em;
}

/* ═══════════════════════════════════════
   COMPOSER
═══════════════════════════════════════ */
.ch-composer {
	background: #ffffff;
	border: 1.5px solid #e5e9f2;
	border-radius: 22px;
	padding: 16px 18px 12px 18px;
	box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04);
	transition: border-color 0.2s ease, box-shadow 0.2s ease;
	display: flex;
	flex-direction: column;
	position: relative;
}

.ch-composer:focus-within {
	border-color: #cbd5e1;
	box-shadow: 0 4px 24px rgba(15, 23, 42, 0.08);
}

.ch-input {
	display: block;
	width: 100%;
	min-height: 44px;
	max-height: 220px;
	border: none !important;
	outline: none !important;
	background: transparent !important;
	box-shadow: none !important;
	font-family: inherit;
	font-size: 15px;
	line-height: 1.5;
	color: #1e293b;
	resize: none;
	padding: 0;
	margin: 0;
}

.ch-input::placeholder {
	color: #64748b;
	font-weight: 400;
}

.ch-toolbar {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-top: 14px;
}

.ch-toolbar-spacer {
	flex: 1;
}

.ch-tool-btn {
	width: 36px;
	height: 36px;
	border-radius: 10px;
	border: 1.5px solid #e2e8f0;
	background: #ffffff;
	color: #4b5563;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	padding: 0;
	transition: all 0.15s ease;
}

.ch-tool-btn:hover:not(:disabled) {
	background: #f8fafc;
	border-color: #cbd5e1;
	color: #0f172a;
}

.ch-tool-btn:disabled {
	opacity: 0.45;
	cursor: not-allowed;
}

.ch-tool-mic {
	border: none;
	background: transparent;
	color: #64748b;
}

.ch-tool-mic:hover:not(:disabled) {
	background: #f1f5f9;
	color: #0f172a;
}

.ch-tool-mic.is-listening {
	color: #ef4444;
	background: #fee2e2;
	animation: pulse 1.2s infinite;
}

@keyframes pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.5; }
}

.ch-send {
	width: 38px;
	height: 38px;
	border-radius: 11px;
	border: none;
	background: #18181b;
	color: #ffffff;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	padding: 0;
	transition: background 0.15s ease, transform 0.12s ease, opacity 0.15s;
	box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.ch-send:hover:not(:disabled) {
	background: #047857;
	transform: translateY(-1px);
	box-shadow: 0 4px 12px rgba(4, 120, 87, 0.3);
}

.ch-send:disabled {
	opacity: 0.32;
	cursor: not-allowed;
}

/* ═══════════════════════════════════════
   SÉPARATEUR "GÉNÉRATION RAPIDE"
═══════════════════════════════════════ */
.ch-below {
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.ch-divider {
	position: relative;
	width: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	margin: 16px 0 6px;
}

.ch-divider-line {
	position: absolute;
	width: 100%;
	height: 1px;
	background: #edf2f7;
	z-index: 1;
}

.ch-divider-badge {
	position: relative;
	z-index: 2;
	background: #ffffff;
	border: 1.5px solid #e5e9f2;
	border-radius: 9999px;
	padding: 4px 18px;
	font-size: 12px;
	font-weight: 500;
	color: #64748b;
	letter-spacing: 0.01em;
	user-select: none;
}

/* ═══════════════════════════════════════
   GRILLE 3 CARTES
═══════════════════════════════════════ */
.ch-cards-grid {
	margin: 0;
	padding: 0;
	list-style: none;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 16px;
}

.ch-card {
	position: relative;
	border-radius: 18px;
	border: 1.5px solid #edf0f5;
	background: #ffffff;
	overflow: hidden;
	padding: 0;
	transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease;
}

.ch-card:hover {
	transform: translateY(-3px);
	box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
	border-color: #e2e8f0;
}

.ch-card-main {
	display: flex;
	flex-direction: column;
	width: 100%;
	height: 100%;
	padding: 8px;
	border: 0;
	border-radius: 16px;
	background: transparent;
	text-align: left;
	font: inherit;
	color: inherit;
	cursor: pointer;
}

.ch-card-main:focus-visible {
	outline: 2px solid #047857;
	outline-offset: -2px;
}

.ch-card-header {
	width: 100%;
	height: 130px;
	border-radius: 14px;
	display: flex;
	align-items: center;
	justify-content: center;
	overflow: hidden;
}

.ch-card-quote .ch-card-header {
	background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 50%, #7c3aed 100%);
}

.ch-card-availability .ch-card-header {
	background: linear-gradient(135deg, #38bdf8 0%, #2563eb 60%, #1d4ed8 100%);
}

.ch-card-approvals .ch-card-header {
	background: linear-gradient(135deg, #34d399 0%, #10b981 50%, #059669 100%);
}

.ch-mock-window {
	width: 86%;
	background: #ffffff;
	border-radius: 8px;
	box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
	padding: 8px 10px;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.ch-window-dots {
	display: flex;
	align-items: center;
	gap: 4px;
}

.ch-dot {
	width: 5px;
	height: 5px;
	border-radius: 50%;
	display: inline-block;
}

.ch-dot-red { background: #ef4444; }
.ch-dot-yellow { background: #f59e0b; }
.ch-dot-green { background: #10b981; }

.ch-code-lines {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.ch-code-row {
	display: flex;
	align-items: center;
	gap: 4px;
}

.ch-code-row.ch-indent {
	padding-left: 8px;
}

.ch-bar {
	height: 4px;
	border-radius: 2px;
	display: inline-block;
}

.ch-bar-thick {
	height: 6px;
	border-radius: 3px;
}

.ch-bar-purple { background: #8b5cf6; }
.ch-bar-dark { background: #1e293b; }
.ch-bar-gray { background: #e2e8f0; }
.ch-bar-slate { background: #cbd5e1; }

.ch-browser-content {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.ch-dash-chips {
	display: flex;
	gap: 3px;
}

.ch-mini-pill {
	width: 8px;
	height: 3px;
	border-radius: 1px;
	background: #93c5fd;
	display: inline-block;
}

.ch-sub-line {
	display: block;
	height: 1px;
	background: #f1f5f9;
	width: 100%;
	margin: 1px 0;
}

.ch-window-dialog {
	gap: 7px;
}

.ch-dialog-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.ch-avatar-wrap {
	display: flex;
	align-items: center;
	gap: 4px;
}

.ch-avatar-circle {
	width: 13px;
	height: 13px;
	border-radius: 50%;
	background: #f472b6;
	display: inline-block;
}

.ch-status-dot-mini {
	width: 4px;
	height: 4px;
	border-radius: 50%;
	background: #3b82f6;
	display: inline-block;
}

.ch-close-x {
	font-size: 9px;
	color: #64748b;
	font-weight: 700;
	line-height: 1;
}

.ch-dialog-content {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.ch-card-body {
	padding: 10px 8px 8px;
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.ch-card-title {
	display: block;
	padding-right: 26px;
	margin: 0;
	font-size: 14px;
	font-weight: 600;
	color: #0f172a;
	line-height: 1.3;
}

.ch-card-link-btn {
	position: absolute;
	right: 14px;
	bottom: 36px;
	border: none;
	background: transparent;
	color: #64748b;
	cursor: pointer;
	padding: 2px;
	border-radius: 4px;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: color 0.15s, background 0.15s;
}

.ch-card-link-btn:hover {
	color: #047857;
	background: #ecfdf5;
}

.ch-card-desc {
	display: block;
	margin: 0;
	font-size: 12px;
	color: #64748b;
	line-height: 1.4;
}

/* ═══════════════════════════════════════
   MODE CONVERSATION (THREAD)
═══════════════════════════════════════ */
.ch-thread {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.is-chat .ch-composer {
	position: sticky;
	bottom: 20px;
	z-index: 5;
}

/* ═══════════════════════════════════════
   ANIMATIONS & TRANSITIONS
═══════════════════════════════════════ */
.ch-fade-enter-active,
.ch-fade-leave-active {
	transition: opacity 0.18s ease, transform 0.18s ease;
}
.ch-fade-enter-from { opacity: 0; transform: translateY(6px); }
.ch-fade-leave-to   { opacity: 0; transform: translateY(-4px); }

/* ═══════════════════════════════════════
   RESPONSIVE
═══════════════════════════════════════ */
@media (max-width: 680px) {
	.cortex-home {
		padding-inline: 12px;
	}
	.ch-cards-grid {
		grid-template-columns: 1fr;
	}
	.ch-subtitle {
		font-size: 22px;
	}
	.ch-top-actions {
		right: 16px;
		top: 14px;
	}
}

/* ═══════════════════════════════════════
   ÉTAT DU MOTEUR, BANNIÈRE, RÉGLAGES
═══════════════════════════════════════ */
.ch-demo-banner {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 14px;
	margin: 0;
	padding: 10px 14px;
	border: 1px solid #f3dfb6;
	border-radius: 12px;
	background: #fff8ea;
	color: #6b4300;
	font-size: 13px;
	line-height: 1.45;
}

.ch-demo-hide {
	flex: none;
	border: 0;
	background: none;
	color: #8a4b00;
	font: inherit;
	font-size: 12.5px;
	font-weight: 600;
	cursor: pointer;
	text-decoration: underline;
}

.ch-status-wrap {
	position: relative;
}

.ch-status {
	display: inline-flex;
	align-items: center;
	gap: 7px;
	height: 32px;
	padding: 0 12px;
	border: 1px solid #e2e8f0;
	border-radius: 999px;
	background: #fff;
	font: inherit;
	font-size: 12.5px;
	font-weight: 600;
	color: #334155;
	cursor: pointer;
	transition: background-color 0.15s ease;
}

.ch-status:hover {
	background: #f8fafc;
}

.ch-status-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: #64748b;
}

.ch-status.is-ai {
	border-color: #bfe5cf;
	background: #f1faf5;
	color: #066336;
}

.ch-status.is-ai .ch-status-dot {
	background: #10b981;
}

.ch-status.is-demo {
	border-color: #f3dfb6;
	background: #fff8ea;
	color: #8a4b00;
}

.ch-status.is-demo .ch-status-dot {
	background: #f59e0b;
}

.ch-pop-wrap {
	position: relative;
}

.ch-pop {
	position: absolute;
	z-index: 30;
	width: 320px;
	max-width: calc(100vw - 32px);
	padding: 14px 16px;
	border: 1px solid #e2e8f0;
	border-radius: 14px;
	background: #fff;
	box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12);
	font-size: 13px;
	color: #334155;
}

.ch-settings {
	top: calc(100% + 10px);
	right: 0;
	display: grid;
	gap: 14px;
}

.ch-status-pop {
	bottom: calc(100% + 10px);
	left: 0;
	line-height: 1.5;
}

.ch-status-pop p {
	margin: 6px 0 0;
}

.ch-pop-title {
	margin: 0;
	font-size: 14px;
	font-weight: 650;
	color: #0f172a;
}

.ch-switch-row,
.ch-pop-row {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 14px;
}

.ch-switch-row small,
.ch-pop-row small {
	display: block;
	margin-top: 2px;
	font-size: 12px;
	color: #6b7a90;
	line-height: 1.4;
}

.ch-switch-row input {
	appearance: none;
	flex: none;
	position: relative;
	width: 34px;
	height: 20px;
	margin: 2px 0 0;
	border-radius: 999px;
	background: #cbd5e1;
	cursor: pointer;
	transition: background-color 0.18s ease;
}

.ch-switch-row input::after {
	content: "";
	position: absolute;
	top: 2px;
	left: 2px;
	width: 16px;
	height: 16px;
	border-radius: 50%;
	background: #fff;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
	transition: transform 0.18s ease;
}

.ch-switch-row input:checked {
	background: #047857;
}

.ch-switch-row input:checked::after {
	transform: translateX(14px);
}

.ch-switch-row input:focus-visible {
	outline: 2px solid #047857;
	outline-offset: 2px;
}

.ch-pop-btn {
	flex: none;
	height: 30px;
	padding: 0 12px;
	border: 1px solid #e2e8f0;
	border-radius: 8px;
	background: #fff;
	font: inherit;
	font-size: 12.5px;
	font-weight: 600;
	color: #334155;
	cursor: pointer;
}

.ch-pop-btn.danger {
	color: #b42318;
	border-color: #f1c9c5;
}

.ch-pop-btn.danger.fill {
	background: #b42318;
	border-color: #b42318;
	color: #fff;
}

.ch-confirm {
	display: inline-flex;
	flex-direction: column;
	gap: 6px;
}

.ch-pop-link {
	justify-self: start;
	padding: 0;
	border: 0;
	background: none;
	color: #066336;
	font: inherit;
	font-size: 13px;
	font-weight: 600;
	cursor: pointer;
}

/* ═══════════════════════════════════════
   HISTORIQUE : TIROIR À DROITE
═══════════════════════════════════════ */
.ch-drawer {
	position: fixed;
	top: 48px;
	right: 0;
	bottom: 0;
	z-index: 1040;
	display: flex;
	flex-direction: column;
	gap: 12px;
	width: 340px;
	max-width: 100vw;
	padding: 18px 16px;
	border-left: 1px solid #e2e8f0;
	background: #fff;
	box-shadow: -12px 0 32px rgba(15, 23, 42, 0.08);
}

.ch-drawer-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.ch-drawer-head h2 {
	margin: 0;
	font-size: 15px;
	font-weight: 650;
	color: #0f172a;
}

.ch-drawer-close {
	width: 30px;
	height: 30px;
	border: 0;
	border-radius: 8px;
	background: transparent;
	color: #64748b;
	cursor: pointer;
}

.ch-drawer-close:hover {
	background: #f1f5f9;
}

.ch-drawer-search {
	width: 100%;
	height: 38px;
	padding: 0 12px;
	border: 1px solid #e2e8f0;
	border-radius: 10px;
	font: inherit;
	font-size: 13.5px;
}

.ch-drawer-search:focus {
	border-color: #047857;
	box-shadow: 0 0 0 3px rgba(4, 120, 87, 0.12);
	outline: none;
}

.ch-drawer-body {
	flex: 1;
	min-height: 0;
	overflow-y: auto;
}

.ch-drawer-empty {
	margin: 8px 2px;
	font-size: 13px;
	line-height: 1.5;
	color: #6b7a90;
}

.ch-drawer-group h3 {
	margin: 14px 4px 6px;
	font-size: 11px;
	font-weight: 700;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: #64748b;
}

.ch-drawer-row {
	display: flex;
	align-items: center;
	gap: 4px;
	border-radius: 10px;
}

.ch-drawer-row:hover,
.ch-drawer-row.current {
	background: #f4f6f9;
}

.ch-drawer-row.current {
	box-shadow: inset 3px 0 0 #047857;
}

.ch-drawer-open {
	flex: 1;
	min-width: 0;
	display: grid;
	gap: 1px;
	padding: 8px 10px;
	border: 0;
	background: transparent;
	text-align: left;
	font: inherit;
	cursor: pointer;
}

.ch-drawer-label {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 13.5px;
	color: #1e293b;
}

.ch-drawer-when {
	font-size: 11.5px;
	color: #64748b;
}

.ch-drawer-del {
	flex: none;
	width: 30px;
	height: 30px;
	margin-right: 4px;
	display: grid;
	place-items: center;
	border: 0;
	border-radius: 8px;
	background: transparent;
	color: #64748b;
	cursor: pointer;
	opacity: 0;
	transition: opacity 0.12s ease, color 0.12s ease;
}

.ch-drawer-row:hover .ch-drawer-del,
.ch-drawer-del:focus-visible {
	opacity: 1;
}

.ch-drawer-del:hover {
	color: #b42318;
	background: #fbeaea;
}

.ch-drawer-confirm {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	padding: 8px 10px;
	font-size: 12.5px;
}

.ch-slide-enter-active,
.ch-slide-leave-active {
	transition: transform 0.22s cubic-bezier(0.2, 0.7, 0.2, 1), opacity 0.22s ease;
}

.ch-slide-enter-from,
.ch-slide-leave-to {
	transform: translateX(24px);
	opacity: 0;
}

@media (hover: none) {
	.ch-drawer-del {
		opacity: 1;
	}
}

@media (prefers-reduced-motion: reduce) {
	.ch-slide-enter-active,
	.ch-slide-leave-active,
	.ch-fade-enter-active,
	.ch-fade-leave-active {
		transition: none;
	}
}
</style>
