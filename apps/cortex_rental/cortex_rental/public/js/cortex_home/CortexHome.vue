<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
import CopilotConversation from "../cortex_copilot/CopilotConversation.vue";
import { sendMessage, getMessages, listSessions, resolveDeskContext } from "../cortex_copilot/chatClient.js";

const ACTION_CARDS = [
	{
		id: "quote",
		title: "Nouvelle location",
		desc: "Créer un devis ou contrat de location d'équipement",
		route: ["Form", "Cortex Rental Transaction", "new"],
		gradient: "purple",
		prompt: "Je souhaite préparer un nouveau devis de location. Affiche-moi les caméras et équipements disponibles au catalogue.",
	},
	{
		id: "availability",
		title: "Grille de disponibilité",
		desc: "Consulter les créneaux et conflits d'inventaire",
		route: ["cortex-availability"],
		gradient: "blue",
		prompt: "Vérifie la disponibilité actuelle du parc d'équipements et signale les éventuels créneaux réservés.",
	},
	{
		id: "approvals",
		title: "Demandes d'approbation",
		desc: "Valider ou réviser les décisions d'agent en attente",
		route: ["List", "Approval Request"],
		gradient: "emerald",
		prompt: "Quelles sont les demandes d'approbation actuellement en attente de décision humaine pour notre société ?",
	},
];

const messages = ref([]);
const sending = ref(false);
const chatSessionId = ref(null);
const text = ref("");
const sessions = ref([]);
const sessionsError = ref("");
const showHistory = ref(false);
const showModelMenu = ref(false);
const isListening = ref(false);
const inputRef = ref(null);
const endRef = ref(null);
const fileInputRef = ref(null);
const attachments = ref([]);
let nextId = 1;
let speechRec = null;

const inConversation = computed(() => messages.value.length > 0 || sending.value);

const firstName = computed(() => {
	try { return frappe.user.first_name() || ""; } catch (e) { return ""; }
});
const displayName = computed(() => {
	try {
		const fn = frappe.user.first_name();
		if (fn && fn !== "Administrator" && fn !== "Dev") return fn;
		const full = frappe.user.full_name();
		if (full && full !== "Administrator" && full !== "Dev") return full;
		if (frappe.boot?.user?.first_name && frappe.boot.user.first_name !== "Administrator") {
			return frappe.boot.user.first_name;
		}
	} catch (e) {}
	return "Kael";
});

const greeting = computed(() => {
	const h = new Date().getHours();
	const moment = h < 12 ? "Bonjour" : h < 18 ? "Bon après-midi" : "Bonsoir";
	return displayName.value ? `${moment}, ${displayName.value}.` : `${moment}.`;
});

const canSend = computed(() => (text.value.trim().length > 0 || attachments.value.length > 0) && !sending.value);

function go(route) { frappe.set_route(route); }

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

function push(msg) { messages.value.push({ id: nextId++, ...msg }); }

function triggerFileInput() {
	if (fileInputRef.value) {
		fileInputRef.value.click();
	}
}

function onFilesSelected(e) {
	const files = Array.from(e.target.files || []);
	for (const file of files) {
		const isImg = file.type.startsWith("image/");
		const preview = isImg ? URL.createObjectURL(file) : null;
		attachments.value.push({
			name: file.name,
			preview,
			isImage: isImg,
		});
	}
	e.target.value = "";
	nextTick(resize);
}

function removeAttachment(idx) {
	attachments.value.splice(idx, 1);
}

function toggleVoice() {
	const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
	if (!SpeechRec) {
		frappe.show_alert({ message: "La saisie vocale n'est pas supportée dans ce navigateur.", indicator: "orange" }, 5);
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
		speechRec.onstart = () => { isListening.value = true; };
		speechRec.onresult = (evt) => {
			const transcript = evt.results[0][0].transcript;
			text.value = text.value ? `${text.value} ${transcript}` : transcript;
			nextTick(resize);
		};
		speechRec.onerror = () => { isListening.value = false; };
		speechRec.onend = () => { isListening.value = false; };
		speechRec.start();
	} catch (e) {
		isListening.value = false;
	}
}

function triggerQuickAction(card) {
	if (card.prompt) {
		submit(card.prompt);
	}
}

async function submit(value) {
	let message = (value !== undefined ? value : text.value).trim();
	if (attachments.value.length > 0 && !message) {
		message = "Analyse des documents joints : " + attachments.value.map(a => a.name).join(", ");
	}
	if (!message || sending.value) return;

	text.value = "";
	attachments.value = [];
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
	attachments.value = [];
	text.value = "";
	nextTick(() => inputRef.value && inputRef.value.focus());
}

function toggleHistory() {
	showHistory.value = !showHistory.value;
	if (showHistory.value && !sessions.value.length) {
		refresh();
	}
}

function openSettings() {
	frappe.set_route(["List", "Cortex Setting"]);
}

function sessionLabel(session) {
	const when = session.last_message_at || session.started_at;
	if (!when) return "Conversation";
	try {
		return "Conversation du " + frappe.datetime.str_to_user(when.slice(0, 16));
	} catch (e) { return "Conversation"; }
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
		<!-- ═══ BOUTONS ACTION EN HAUT À DROITE ═══ -->
		<header class="ch-top-actions" aria-label="Navigation rapide">
			<button
				type="button"
				class="ch-top-btn"
				title="Nouvelle conversation"
				aria-label="Nouvelle conversation"
				@click="newConversation"
			>
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M12 20h9"/>
					<path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
				</svg>
			</button>
			<button
				type="button"
				class="ch-top-btn"
				:class="{ 'is-active': showHistory }"
				title="Historique des conversations"
				aria-label="Historique des conversations"
				@click="toggleHistory"
			>
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="12" cy="12" r="10"/>
					<polyline points="12 6 12 12 16 14"/>
				</svg>
			</button>
			<button
				type="button"
				class="ch-top-btn"
				title="Paramètres Cortex"
				aria-label="Paramètres Cortex"
				@click="openSettings"
			>
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="12" cy="12" r="3"/>
					<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
				</svg>
			</button>
		</header>

		<section class="ch-stage">
			<!-- ═══ HERO (espacement accru, titre moins bold, nom d'utilisateur réel) ═══ -->
			<Transition name="ch-fade" mode="out-in">
				<header v-if="!inConversation" key="hero" class="ch-hero">
					<h1 class="ch-title">{{ greeting }}</h1>
					<p class="ch-subtitle">Comment puis-je vous aider aujourd'hui&nbsp;?</p>
				</header>

				<!-- ═══ MODE CONVERSATION THREAD ═══ -->
				<div v-else key="chat" class="ch-thread">
					<div class="ch-thread-bar">
						<button type="button" class="ch-link" @click="newConversation">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
								<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
							</svg>
							Nouvelle conversation
						</button>
					</div>
					<CopilotConversation :messages="messages" :sending="sending" @continue="submit" @retry="retry" />
					<div ref="endRef"></div>
				</div>
			</Transition>

			<!-- ═══ COMPOSER RÉPLIQUE PIXEL-PERFECT ═══ -->
			<form class="ch-composer" @submit.prevent="submit()">
				<!-- Fichiers joints en haut -->
				<div v-if="attachments.length > 0" class="ch-attachments-row">
					<div v-for="(att, idx) in attachments" :key="idx" class="ch-attachment-chip">
						<img v-if="att.preview" :src="att.preview" class="ch-att-thumb" alt="Aperçu" />
						<div v-else class="ch-att-fallback">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
								<polyline points="14 2 14 8 20 8"/>
							</svg>
						</div>
						<span class="ch-att-name">{{ att.name }}</span>
						<button type="button" class="ch-att-remove" aria-label="Supprimer" @click.stop="removeAttachment(idx)">
							<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
								<line x1="18" y1="6" x2="6" y2="18"/>
								<line x1="6" y1="6" x2="18" y2="18"/>
							</svg>
						</button>
					</div>
				</div>

				<!-- Hidden file input triggered by + button -->
				<input
					ref="fileInputRef"
					type="file"
					multiple
					accept="image/*,.pdf,.doc,.docx"
					class="ch-sr"
					@change="onFilesSelected"
				/>

				<!-- Zone de saisie principale -->
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

				<!-- Rangée du bas : [+] [Cortex 3.0 ▾] [spacer] [🎤] [ ↑ ] -->
				<div class="ch-toolbar">
					<!-- Bouton + (ajouter fichiers ou pièces jointes) -->
					<button
						type="button"
						class="ch-tool-btn ch-tool-plus"
						title="Joindre des fichiers ou images"
						aria-label="Joindre des fichiers"
						@click="triggerFileInput"
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<line x1="12" y1="5" x2="12" y2="19"/>
							<line x1="5" y1="12" x2="19" y2="12"/>
						</svg>
					</button>

					<!-- Sélecteur modèle Kana 3.0 / Cortex 3.0 avec chevron -->
					<div class="ch-model-pill-wrap">
						<button
							type="button"
							class="ch-model-pill"
							title="Moteur IA : Cortex Copilot 3.0"
							@click="showModelMenu = !showModelMenu"
						>
							<span>Cortex 3.0</span>
							<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
								<polyline points="6 9 12 15 18 9"/>
							</svg>
						</button>
						<div v-if="showModelMenu" class="ch-model-dropdown">
							<div class="ch-model-item is-active">
								<strong>Cortex Copilot 3.0</strong>
								<span>Passerelle IA & Outils Frappe</span>
							</div>
							<div class="ch-model-footer">
								Connecté aux outils métier réels
							</div>
						</div>
					</div>

					<div class="ch-toolbar-spacer"></div>

					<!-- Icône microphone (saisie vocale Web Speech API) -->
					<button
						type="button"
						class="ch-tool-btn ch-tool-mic"
						:class="{ 'is-listening': isListening }"
						:title="isListening ? 'Arrêter l\'écoute' : 'Activer la saisie vocale'"
						aria-label="Saisie vocale"
						@click="toggleVoice"
					>
						<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
							<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
							<line x1="12" y1="19" x2="12" y2="22"/>
						</svg>
					</button>

					<!-- Bouton envoyer — carré arrondi noir avec flèche blanche -->
					<button
						type="submit"
						class="ch-send"
						:disabled="!canSend"
						aria-label="Envoyer"
					>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
							<line x1="12" y1="19" x2="12" y2="5"/>
							<polyline points="5 12 12 5 19 12"/>
						</svg>
					</button>
				</div>
			</form>

			<!-- ═══ ZONE SOUS LE COMPOSER ═══ -->
			<Transition name="ch-fade">
				<div v-if="!inConversation" class="ch-below">

					<!-- Séparateur "Génération rapide" avec pill au milieu -->
					<div class="ch-divider">
						<div class="ch-divider-line"></div>
						<div class="ch-divider-badge">Génération rapide</div>
					</div>

					<!-- Grille 3 colonnes de cartes illustrées — 100% fonctionnelles end-to-end -->
					<div class="ch-cards-grid" role="list" aria-label="Actions de génération rapide">
						<!-- CARTE 1 : Violette — Générer un devis / location (Code window style) -->
						<div
							role="listitem"
							class="ch-card ch-card-purple"
							@click="triggerQuickAction(ACTION_CARDS[0])"
						>
							<div class="ch-card-header">
								<div class="ch-mock-window ch-window-code">
									<div class="ch-window-dots">
										<span class="ch-dot ch-dot-red"></span>
										<span class="ch-dot ch-dot-yellow"></span>
										<span class="ch-dot ch-dot-green"></span>
									</div>
									<div class="ch-code-lines">
										<div class="ch-code-row">
											<span class="ch-bar ch-bar-purple" style="width: 28px;"></span>
											<span class="ch-bar ch-bar-gray" style="width: 50px;"></span>
										</div>
										<div class="ch-code-row">
											<span class="ch-bar ch-bar-purple" style="width: 20px;"></span>
											<span class="ch-bar ch-bar-dark" style="width: 36px;"></span>
										</div>
										<div class="ch-code-row ch-indent">
											<span class="ch-bar ch-bar-purple" style="width: 32px;"></span>
											<span class="ch-bar ch-bar-gray" style="width: 22px;"></span>
										</div>
										<div class="ch-code-row ch-indent">
											<span class="ch-bar ch-bar-purple" style="width: 16px;"></span>
										</div>
										<div class="ch-code-row">
											<span class="ch-bar ch-bar-dark" style="width: 30px;"></span>
										</div>
									</div>
								</div>
							</div>
							<div class="ch-card-body">
								<div class="ch-card-title-row">
									<h2 class="ch-card-title">{{ ACTION_CARDS[0].title }}</h2>
									<button
										type="button"
										class="ch-card-link-btn"
										title="Ouvrir le formulaire ERPNext"
										aria-label="Ouvrir le formulaire"
										@click.stop="go(ACTION_CARDS[0].route)"
									>
										<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
											<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
											<polyline points="15 3 21 3 21 9"/>
											<line x1="10" y1="14" x2="21" y2="3"/>
										</svg>
									</button>
								</div>
								<p class="ch-card-desc">{{ ACTION_CARDS[0].desc }}</p>
							</div>
						</div>

						<!-- CARTE 2 : Bleue — Disponibilité (Browser / Analytics table style) -->
						<div
							role="listitem"
							class="ch-card ch-card-blue"
							@click="triggerQuickAction(ACTION_CARDS[1])"
						>
							<div class="ch-card-header">
								<div class="ch-mock-window ch-window-browser">
									<div class="ch-window-dots">
										<span class="ch-dot ch-dot-red"></span>
										<span class="ch-dot ch-dot-yellow"></span>
										<span class="ch-dot ch-dot-green"></span>
									</div>
									<div class="ch-browser-content">
										<div class="ch-bar ch-bar-dark ch-bar-thick" style="width: 38px;"></div>
										<div class="ch-dash-chips">
											<span class="ch-mini-pill"></span>
											<span class="ch-mini-pill"></span>
											<span class="ch-mini-pill"></span>
										</div>
										<div class="ch-sub-line"></div>
										<div class="ch-bar ch-bar-slate" style="width: 82%;"></div>
										<div class="ch-bar ch-bar-gray" style="width: 65%;"></div>
										<div class="ch-bar ch-bar-gray" style="width: 75%;"></div>
									</div>
								</div>
							</div>
							<div class="ch-card-body">
								<div class="ch-card-title-row">
									<h2 class="ch-card-title">{{ ACTION_CARDS[1].title }}</h2>
									<button
										type="button"
										class="ch-card-link-btn"
										title="Ouvrir la matrice de disponibilité"
										aria-label="Ouvrir la disponibilité"
										@click.stop="go(ACTION_CARDS[1].route)"
									>
										<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
											<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
											<polyline points="15 3 21 3 21 9"/>
											<line x1="10" y1="14" x2="21" y2="3"/>
										</svg>
									</button>
								</div>
								<p class="ch-card-desc">{{ ACTION_CARDS[1].desc }}</p>
							</div>
						</div>

						<!-- CARTE 3 : Verte émeraude — Approbations (Notification card dialog style) -->
						<div
							role="listitem"
							class="ch-card ch-card-emerald"
							@click="triggerQuickAction(ACTION_CARDS[2])"
						>
							<div class="ch-card-header">
								<div class="ch-mock-window ch-window-dialog">
									<div class="ch-dialog-top">
										<div class="ch-avatar-wrap">
											<span class="ch-avatar-circle"></span>
											<span class="ch-status-dot"></span>
										</div>
										<span class="ch-close-x">✕</span>
									</div>
									<div class="ch-dialog-content">
										<div class="ch-bar ch-bar-slate" style="width: 68%;"></div>
										<div class="ch-bar ch-bar-gray" style="width: 88%;"></div>
										<div class="ch-bar ch-bar-gray" style="width: 48%;"></div>
									</div>
								</div>
							</div>
							<div class="ch-card-body">
								<div class="ch-card-title-row">
									<h2 class="ch-card-title">{{ ACTION_CARDS[2].title }}</h2>
									<button
										type="button"
										class="ch-card-link-btn"
										title="Ouvrir les approbations"
										aria-label="Ouvrir les approbations"
										@click.stop="go(ACTION_CARDS[2].route)"
									>
										<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
											<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
											<polyline points="15 3 21 3 21 9"/>
											<line x1="10" y1="14" x2="21" y2="3"/>
										</svg>
									</button>
								</div>
								<p class="ch-card-desc">{{ ACTION_CARDS[2].desc }}</p>
							</div>
						</div>
					</div>

					<!-- Historique des conversations -->
					<div v-if="showHistory || sessions.length > 0" class="ch-history-section">
						<div class="ch-history-header">
							<span class="ch-history-title">Conversations récentes</span>
							<button type="button" class="ch-history-close" @click="showHistory = false">Masquer</button>
						</div>
						<div class="ch-recent-list">
							<button
								v-for="session in sessions"
								:key="session.name"
								type="button"
								class="ch-recent-row"
								@click="openSession(session.name)"
							>
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
								</svg>
								<span>{{ sessionLabel(session) }}</span>
							</button>
						</div>
					</div>

				</div>
			</Transition>
		</section>
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
	padding: 16px 24px 100px;
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
	max-width: 740px;
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
	padding-top: clamp(64px, 14vh, 120px);
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
	color: #7487a3;
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

.ch-attachments-row {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-bottom: 12px;
}

.ch-attachment-chip {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	background: #f1f4f9;
	border-radius: 8px;
	padding: 4px 10px 4px 4px;
	font-size: 13px;
	color: #334155;
	font-weight: 500;
}

.ch-att-thumb {
	width: 28px;
	height: 28px;
	border-radius: 6px;
	object-fit: cover;
}

.ch-att-fallback {
	width: 28px;
	height: 28px;
	border-radius: 6px;
	background: #e2e8f0;
	display: flex;
	align-items: center;
	justify-content: center;
	color: #64748b;
}

.ch-att-name {
	max-width: 140px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.ch-att-remove {
	border: none;
	background: transparent;
	color: #94a3b8;
	cursor: pointer;
	padding: 0;
	display: flex;
	align-items: center;
	justify-content: center;
}

.ch-att-remove:hover {
	color: #ef4444;
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
	color: #94a3b8;
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

.ch-model-pill-wrap {
	position: relative;
}

.ch-model-pill {
	height: 36px;
	padding: 0 12px;
	border-radius: 10px;
	border: none;
	background: transparent;
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-size: 14px;
	font-weight: 600;
	color: #1e293b;
	cursor: pointer;
	user-select: none;
	transition: background 0.15s;
}

.ch-model-pill:hover {
	background: #f1f5f9;
}

.ch-model-pill svg {
	color: #64748b;
}

.ch-model-dropdown {
	position: absolute;
	bottom: calc(100% + 8px);
	left: 0;
	width: 220px;
	background: #ffffff;
	border: 1.5px solid #e2e8f0;
	border-radius: 12px;
	box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
	padding: 8px;
	z-index: 20;
}

.ch-model-item {
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding: 8px 10px;
	border-radius: 8px;
	background: #f8fafc;
	font-size: 13px;
	color: #1e293b;
}

.ch-model-item span {
	font-size: 11px;
	color: #64748b;
}

.ch-model-footer {
	margin-top: 6px;
	padding-top: 6px;
	border-top: 1px solid #f1f5f9;
	font-size: 11px;
	color: #10b981;
	text-align: center;
	font-weight: 500;
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
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 16px;
}

.ch-card {
	border-radius: 18px;
	border: 1.5px solid #edf0f5;
	background: #ffffff;
	overflow: hidden;
	padding: 8px;
	display: flex;
	flex-direction: column;
	cursor: pointer;
	text-align: left;
	font: inherit;
	transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease;
}

.ch-card:hover {
	transform: translateY(-3px);
	box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
	border-color: #e2e8f0;
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

.ch-card-purple .ch-card-header {
	background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 50%, #7c3aed 100%);
}

.ch-card-blue .ch-card-header {
	background: linear-gradient(135deg, #38bdf8 0%, #2563eb 60%, #1d4ed8 100%);
}

.ch-card-emerald .ch-card-header {
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

.ch-status-dot {
	width: 4px;
	height: 4px;
	border-radius: 50%;
	background: #3b82f6;
	display: inline-block;
}

.ch-close-x {
	font-size: 9px;
	color: #94a3b8;
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

.ch-card-title-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 6px;
}

.ch-card-title {
	margin: 0;
	font-size: 14px;
	font-weight: 600;
	color: #0f172a;
	line-height: 1.3;
}

.ch-card-link-btn {
	border: none;
	background: transparent;
	color: #94a3b8;
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
	margin: 0;
	font-size: 12px;
	color: #64748b;
	line-height: 1.4;
}

/* ═══════════════════════════════════════
   HISTORIQUE
═══════════════════════════════════════ */
.ch-history-section {
	background: #ffffff;
	border: 1.5px solid #edf0f5;
	border-radius: 16px;
	padding: 14px 16px;
	margin-top: 4px;
}

.ch-history-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 10px;
}

.ch-history-title {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: #94a3b8;
}

.ch-history-close {
	border: none;
	background: transparent;
	font-size: 12px;
	color: #64748b;
	cursor: pointer;
	padding: 0;
}

.ch-history-close:hover {
	color: #0f172a;
}

.ch-recent-list {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.ch-recent-row {
	display: flex;
	align-items: center;
	gap: 10px;
	width: 100%;
	padding: 8px 10px;
	border: none;
	border-radius: 8px;
	background: transparent;
	font-family: inherit;
	font-size: 13px;
	color: #475569;
	text-align: left;
	cursor: pointer;
	transition: background 0.12s, color 0.12s;
}

.ch-recent-row:hover {
	background: #f8fafc;
	color: #0f172a;
}

/* ═══════════════════════════════════════
   MODE CONVERSATION (THREAD)
═══════════════════════════════════════ */
.ch-thread {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.ch-thread-bar {
	display: flex;
	align-items: center;
	padding: 6px 0;
}

.ch-link {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	height: 32px;
	padding: 0 12px;
	border: none;
	background: #f1f5f9;
	color: #475569;
	font-family: inherit;
	font-size: 13px;
	font-weight: 500;
	cursor: pointer;
	border-radius: 8px;
	transition: background 0.12s, color 0.12s;
}

.ch-link:hover {
	background: #e2e8f0;
	color: #0f172a;
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
</style>
