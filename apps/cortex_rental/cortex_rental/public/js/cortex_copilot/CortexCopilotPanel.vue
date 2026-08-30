<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import CopilotHeader from "./CopilotHeader.vue";
import CopilotContextBar from "./CopilotContextBar.vue";
import CopilotQuickActions from "./CopilotQuickActions.vue";
import CopilotConversation from "./CopilotConversation.vue";
import CopilotComposer from "./CopilotComposer.vue";
import { sendMessage, resolveDeskContext } from "./chatClient.js";

const props = defineProps({
	// 'floating': slide-in overlay (global mount, cortex_copilot.bundle.js).
	// 'docked': full-page layout (the /app/cortex-assistant Page).
	mode: { type: String, default: "floating" },
});

const WIDTH_STORAGE_KEY = "cortex_copilot_panel_width";
const MIN_WIDTH = 360;
const MAX_WIDTH = 560;
const DEFAULT_WIDTH = 400;

const isOpen = ref(props.mode === "docked");
const width = ref(readStoredWidth());
const messages = ref([]);
const sending = ref(false);
const chatSessionId = ref(null);
const context = ref(resolveDeskContext());
// Whether the currently-open document (context.active_doctype/name) is
// included in the next message — the one real toggle in
// CopilotContextBar's "Modifier le contexte" editor. Resets to true
// whenever the referenced document itself changes: this is a
// per-message decision, not a sticky preference that should silently
// carry over onto an unrelated document.
const shareReference = ref(true);
const composerRef = ref(null);
const launcherRef = ref(null);
let resizing = false;

function setContext(next) {
	if (next.active_document_name !== context.value.active_document_name) {
		shareReference.value = true;
	}
	context.value = next;
}

function outgoingContext() {
	if (shareReference.value || !context.value.active_doctype) return context.value;
	const { active_doctype, active_document_name, ...rest } = context.value;
	return rest;
}

function readStoredWidth() {
	try {
		const stored = Number(window.localStorage.getItem(WIDTH_STORAGE_KEY));
		if (stored >= MIN_WIDTH && stored <= MAX_WIDTH) return stored;
	} catch (e) {
		// localStorage unavailable (private browsing, etc.) — fall back silently.
	}
	return DEFAULT_WIDTH;
}

function open(focusComposer) {
	isOpen.value = true;
	setContext(resolveDeskContext());
	if (focusComposer) {
		nextTick(() => {
			const el = document.querySelector(".cp-composer-input");
			if (el) el.focus();
		});
	}
}

function close() {
	if (props.mode === "docked") return; // the detached page has no "closed" state
	isOpen.value = false;
	if (launcherRef.value) launcherRef.value.focus();
}

function toggle() {
	if (isOpen.value) close();
	else open(true);
}

function detach() {
	frappe.set_route("cortex-assistant");
}

let nextId = 1;
function pushMessage(msg) {
	messages.value.push({ id: nextId++, ...msg });
}

async function handleSend(text) {
	pushMessage({ role: "user", text });
	sending.value = true;
	setContext(resolveDeskContext());

	try {
		const response = await sendMessage(text, outgoingContext(), chatSessionId.value);
		chatSessionId.value = response.chat_session_id || chatSessionId.value;
		pushMessage({ role: "assistant", blocks: response.blocks || [] });
	} catch (err) {
		pushMessage({
			role: "assistant",
			blocks: [{ type: "error", title: "Erreur", safe_message: err.message, retry_allowed: true }],
		});
	} finally {
		sending.value = false;
	}
}

function handleContinue(text) {
	handleSend(text);
}

function handleRetry() {
	const lastUser = [...messages.value].reverse().find((m) => m.role === "user");
	if (lastUser) handleSend(lastUser.text);
}

// ---- Resizing (floating mode only) ----
function startResize(e) {
	if (props.mode !== "floating") return;
	resizing = true;
	e.preventDefault();
}
function onResizeMove(e) {
	if (!resizing) return;
	const next = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, window.innerWidth - e.clientX));
	width.value = next;
}
function stopResize() {
	if (!resizing) return;
	resizing = false;
	try {
		window.localStorage.setItem(WIDTH_STORAGE_KEY, String(width.value));
	} catch (e) {
		// ignore — same private-browsing fallback as readStoredWidth
	}
}

// ---- Keyboard: Cmd/Ctrl+J toggles, Escape closes (floating only) ----
function onKeydown(e) {
	if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
		e.preventDefault();
		toggle();
	} else if (e.key === "Escape" && isOpen.value && props.mode === "floating") {
		close();
	}
}

// ---- Live context reactivity while the panel stays open ----
// frappe.router.on('change', ...) is a real, documented Frappe client
// event (verified before use — see CHANGELOG.md, ninth wave) — not the
// same thing as frappe.route.on, an older/deprecated form found in
// some pre-2018 references that was not used here. Only updates the
// *displayed* context bar / next-send payload; it never touches an
// in-flight or already-sent message.
function onRouteChange() {
	if (props.mode === "floating" && !isOpen.value) return;
	setContext(resolveDeskContext());
}

onMounted(() => {
	window.addEventListener("keydown", onKeydown);
	window.addEventListener("mousemove", onResizeMove);
	window.addEventListener("mouseup", stopResize);
	if (typeof frappe !== "undefined" && frappe.router && frappe.router.on) {
		frappe.router.on("change", onRouteChange);
	}
});
onBeforeUnmount(() => {
	window.removeEventListener("keydown", onKeydown);
	window.removeEventListener("mousemove", onResizeMove);
	window.removeEventListener("mouseup", stopResize);
	if (typeof frappe !== "undefined" && frappe.router && frappe.router.off) {
		frappe.router.off("change", onRouteChange);
	}
});

const panelStyle = computed(() =>
	props.mode === "floating" ? { width: width.value + "px" } : {},
);
</script>

<template>
	<div class="cortex-app cp-root" :class="mode">
		<button
			v-if="mode === 'floating' && !isOpen"
			ref="launcherRef"
			class="cp-launcher"
			aria-label="Ouvrir Cortex Copilot (⌘J)"
			title="Cortex Copilot (⌘J / Ctrl+J)"
			@click="open(false)"
		>
			✦
		</button>

		<div v-if="mode === 'docked' || isOpen" class="cp-panel" :class="mode" :style="panelStyle" role="complementary" aria-label="Cortex Copilot">
			<div v-if="mode === 'floating'" class="cp-resize-handle" @mousedown="startResize"></div>
			<CopilotHeader
				subtitle="Cortex peut expliquer, préparer et signaler — jamais exécuter seul."
				:detach-href="mode === 'floating' ? '#' : ''"
				:closable="mode === 'floating'"
				@close="close"
				@detach="detach"
			/>
			<CopilotContextBar
				:context="context"
				:share-reference="shareReference"
				@update:share-reference="shareReference = $event"
			/>
			<CopilotQuickActions :page="context.page" :disabled="sending" @run="handleSend" />
			<CopilotConversation :messages="messages" :sending="sending" @continue="handleContinue" @retry="handleRetry" />
			<CopilotComposer ref="composerRef" :disabled="sending" @send="handleSend" />
		</div>
	</div>
</template>

<style scoped>
.cp-root.floating {
	position: fixed;
	inset: 0;
	pointer-events: none;
	z-index: 100;
}
.cp-launcher {
	position: fixed;
	right: var(--space-6);
	bottom: var(--space-6);
	width: 48px;
	height: 48px;
	border-radius: 50%;
	background: var(--cortex-primary-600);
	color: var(--cortex-inverse);
	border: none;
	font-size: 20px;
	cursor: pointer;
	box-shadow: var(--shadow-md);
	pointer-events: auto;
}
.cp-launcher:hover {
	background: var(--cortex-primary-700);
}

.cp-panel {
	display: flex;
	flex-direction: column;
	background: var(--cortex-surface);
}
.cp-panel.floating {
	position: fixed;
	top: var(--navbar-height, 56px);
	right: 0;
	bottom: 0;
	border-left: 1px solid var(--cortex-border);
	box-shadow: var(--shadow-md);
	pointer-events: auto;
}
.cp-panel.docked {
	width: 100%;
	height: calc(100vh - var(--navbar-height, 56px) - 40px);
	max-width: 720px;
	margin: 0 auto;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-lg);
}
.cp-resize-handle {
	position: absolute;
	left: -3px;
	top: 0;
	bottom: 0;
	width: 6px;
	cursor: ew-resize;
	pointer-events: auto;
}
</style>
