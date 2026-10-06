<script setup>
// Ce que l'assistant a consulté, en une ligne discrète. Le libellé « shimmer » le temps d'un instant à l'arrivée
// (animation seulement : l'outil a déjà été appelé par le serveur).
import { ref, onMounted } from "vue";

const props = defineProps({
	block: { type: Object, required: true }, // {tool_name, state, message}
	animate: { type: Boolean, default: false },
});

const working = ref(props.animate && props.block.state !== "failed");
const reduced = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

onMounted(() => {
	if (working.value && !reduced) window.setTimeout(() => (working.value = false), 700);
	else working.value = false;
});
</script>

<template>
	<p class="cp-tool" :class="{ 'is-working': working, 'is-failed': block.state === 'failed' }">
		<span class="cp-tool-glyph" aria-hidden="true">{{ block.state === "failed" ? "✕" : working ? "" : "✓" }}</span>
		<span class="cp-tool-label" :class="{ 'cp-shimmer': working }">{{ block.tool_name }}</span>
		<span v-if="block.message" class="cp-tool-msg">· {{ block.message }}</span>
	</p>
</template>

<style scoped>
.cp-tool {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 0;
	font-size: 12.5px;
	color: #64748b;
}
.cp-tool-glyph {
	width: 12px;
	font-size: 11px;
	color: #64748b;
}
.cp-tool.is-failed {
	color: #9b2c20;
}
.cp-shimmer {
	background: linear-gradient(90deg, #94a3b8 0%, #0f172a 45%, #94a3b8 90%);
	background-size: 220% 100%;
	-webkit-background-clip: text;
	background-clip: text;
	-webkit-text-fill-color: transparent;
	animation: cp-shimmer 1.3s linear infinite;
}
@keyframes cp-shimmer {
	from {
		background-position: 120% 0;
	}
	to {
		background-position: -100% 0;
	}
}
@media (prefers-reduced-motion: reduce) {
	.cp-shimmer {
		animation: none;
		-webkit-text-fill-color: currentColor;
		background: none;
	}
}
</style>
