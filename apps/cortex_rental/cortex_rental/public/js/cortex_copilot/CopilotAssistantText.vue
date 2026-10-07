<script setup>
// Texte de l'assistant : du texte normal, sans cadre. Quand la réponse vient d'arriver, il apparaît mot à mot
// (animation d'affichage d'un texte déjà reçu ; ce n'est pas un flux du modèle). Sans animation si le système
// demande de réduire les mouvements.
import { ref, computed, onMounted, onBeforeUnmount } from "vue";

const props = defineProps({
	block: { type: Object, required: true }, // {text}
	animate: { type: Boolean, default: false },
});
const emit = defineEmits(["progress", "revealed"]);

const parts = computed(() => String(props.block.text || "").split(/(\s+)/));
const reduced = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const shown = ref(props.animate && !reduced ? 0 : parts.value.length);
const visible = computed(() => parts.value.slice(0, shown.value).join(""));
let timer = null;

onMounted(() => {
	if (shown.value >= parts.value.length) {
		emit("revealed");
		return;
	}
	// Durée totale bornée (≈ 1,6 s au plus) : un long texte accélère au lieu de faire attendre.
	const total = parts.value.length;
	const step = Math.max(1, Math.ceil(total / 55));
	timer = window.setInterval(() => {
		shown.value = Math.min(total, shown.value + step);
		emit("progress");
		if (shown.value >= total) {
			window.clearInterval(timer);
			emit("revealed");
		}
	}, 28);
});

onBeforeUnmount(() => timer && window.clearInterval(timer));
</script>

<template>
	<p class="cp-assistant-text" :aria-label="animate ? block.text : undefined">{{ visible }}</p>
</template>

<style scoped>
.cp-assistant-text {
	margin: 0;
	font-size: 15px;
	line-height: 1.6;
	color: #1e293b;
	white-space: pre-wrap;
}
</style>
