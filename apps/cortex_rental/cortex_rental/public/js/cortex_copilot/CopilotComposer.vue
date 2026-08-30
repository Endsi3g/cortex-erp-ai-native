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
			aria-label="Message pour Cortex Copilot"
			@keydown="onKeydown"
		></textarea>
		<button class="cx-btn cx-btn-primary" :disabled="disabled || !text.trim()" @click="submit">
			Envoyer
		</button>
	</div>
	<p class="cx-text-meta cp-composer-hint">
		Cortex peut préparer des brouillons et des demandes d'approbation. Les contrats, factures et envois exigent
		une validation humaine. ⌘/Ctrl + Entrée pour envoyer.
	</p>
</template>

<style scoped>
.cp-composer {
	display: flex;
	gap: var(--space-2);
	padding: var(--space-3);
	border-top: 1px solid var(--cortex-border);
	align-items: flex-end;
}
.cp-composer-input {
	flex: 1;
	resize: none;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	padding: var(--space-2) var(--space-3);
	font-family: inherit;
	font-size: 13px;
}
.cp-composer-hint {
	padding: 0 var(--space-3) var(--space-2);
	margin: 0;
}
</style>
