<script setup>
import { ref } from "vue";

const props = defineProps({
	placeholder: { type: String, default: "Demandez à Cortex…" },
	disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["send"]);

const text = ref("");

function submit() {
	const trimmed = text.value.trim();
	if (!trimmed || props.disabled) return;
	emit("send", trimmed);
	text.value = "";
}

function onKeydown(e) {
	if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
		e.preventDefault();
		submit();
	}
}
</script>

<template>
	<div class="cp-composer">
		<textarea
			v-model="text"
			class="cp-composer-input"
			:placeholder="placeholder"
			:disabled="disabled"
			rows="2"
			aria-label="Message pour le copilote Cortex"
			@keydown="onKeydown"
		></textarea>
		<div class="cp-composer-footer">
			<p class="cp-composer-hint">
				Cortex peut préparer des brouillons et des demandes d'approbation.
				Les contrats, factures et envois exigent une validation humaine.
				<kbd>⌘</kbd><kbd>↵</kbd> pour envoyer.
			</p>
			<button
				class="cp-send-btn"
				:disabled="disabled || !text.trim()"
				aria-label="Envoyer"
				@click="submit"
			>
				<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<line x1="12" y1="19" x2="12" y2="5"/>
					<polyline points="5 12 12 5 19 12"/>
				</svg>
			</button>
		</div>
	</div>
</template>

<style scoped>
.cp-composer {
	display: flex;
	flex-direction: column;
	gap: 0;
	border-top: 1px solid var(--cortex-border);
	background: var(--cortex-surface);
}

.cp-composer-input {
	flex: 1;
	resize: none;
	border: 0;
	border-bottom: 1px solid var(--cortex-border);
	border-radius: 0;
	padding: var(--space-3) var(--space-4);
	font-family: inherit;
	font-size: 13.5px;
	line-height: 1.5;
	color: var(--cortex-text);
	background: transparent;
	outline: none;
	transition: background 0.12s;
}

.cp-composer-input::placeholder {
	color: var(--cortex-text-muted);
}

.cp-composer-input:focus {
	background: var(--cortex-surface-subtle, #f4f4f5);
	outline: none;
	box-shadow: none;
}

.cp-composer-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-2);
	padding: var(--space-2) var(--space-3) var(--space-2) var(--space-4);
}

.cp-composer-hint {
	margin: 0;
	font-size: 11.5px;
	line-height: 1.4;
	color: var(--cortex-text-muted);
}

.cp-composer-hint kbd {
	display: inline-block;
	padding: 0 3px;
	font-size: 10px;
	font-family: var(--font-mono, monospace);
	background: var(--cortex-surface-subtle, #f4f4f5);
	border: 1px solid var(--cortex-border);
	border-radius: 3px;
	color: var(--cortex-text-muted);
}

.cp-send-btn {
	flex: none;
	width: 30px;
	height: 30px;
	border-radius: 50%;
	border: 0;
	cursor: pointer;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	background: var(--cortex-text, #09090b);
	color: #fff;
	transition: background 0.15s, transform 0.15s, opacity 0.15s;
	box-shadow: 0 1px 3px rgba(9, 9, 11, 0.18);
}

.cp-send-btn:hover:not(:disabled) {
	background: var(--cortex-emerald-700, #047857);
	transform: translateY(-1px);
}

.cp-send-btn:disabled {
	opacity: 0.3;
	cursor: not-allowed;
}
</style>
