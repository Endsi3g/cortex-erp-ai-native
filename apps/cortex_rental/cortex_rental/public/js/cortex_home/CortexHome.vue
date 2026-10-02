<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
import CopilotConversation from "../cortex_copilot/CopilotConversation.vue";
import { sendMessage, getMessages, listSessions, resolveDeskContext } from "../cortex_copilot/chatClient.js";
import { ICONS } from "../cortex_shared/CortexIcons.js";

const CHIPS = [
	{ label: "Nouvelle location", route: ["Form", "Cortex Rental Transaction", "new"], icon: "plusCircle" },
	{ label: "Grille de disponibilité", route: ["cortex-availability"], icon: "calendar" },
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
const displayName = computed(() => {
	if (firstName.value) return firstName.value;
	try {
		const full = frappe.user.full_name();
		return full && full !== "Administrator" ? full : "";
	} catch (e) {
		return "";
	}
});
const greeting = computed(() => (displayName.value ? `Bonjour ${displayName.value}` : "Bonjour"));
const today = computed(() => {
	const label = new Date().toLocaleDateString("fr-CA", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
	return label.charAt(0).toUpperCase() + label.slice(1);
});
const identity = computed(() => frappe.boot.cortex_home || {});
const logoUrl = computed(() => identity.value.company_logo || "/assets/cortex_rental/images/cortex-logo.svg");
const logoAlt = computed(() => (identity.value.company ? `Logo de ${identity.value.company}` : "Logo Cortex"));

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
					<img class="ch-logo" :src="logoUrl" :alt="logoAlt" />
					<h1 class="ch-title">{{ greeting }}</h1>
					<p class="ch-date">{{ today }}</p>
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
					placeholder="Que puis-je faire pour vous ?"
					:disabled="sending"
					@input="resize"
					@keydown="onKeydown"
				></textarea>
				<div class="ch-composer-row">
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
