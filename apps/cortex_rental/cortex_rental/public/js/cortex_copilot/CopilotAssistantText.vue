<script setup>
// Texte de l'assistant : jamais un fait vérifié (ceux-ci passent par le bloc « fait vérifié »).
defineProps({
	block: { type: Object, required: true }, // {text}
});
</script>

<template>
	<p class="cp-assistant-text">{{ block.text }}</p>
</template>

<style scoped>
.cp-assistant-text {
	margin: 0;
	font-size: 14.5px;
	line-height: 1.55;
	color: #1e293b;
	white-space: pre-wrap;
}
</style>
