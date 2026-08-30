<script setup>
import { ref } from "vue";

const props = defineProps({
	context: { type: Object, required: true }, // resolveDeskContext() shape
	shareReference: { type: Boolean, required: true },
});
const emit = defineEmits(["update:shareReference"]);

const PAGE_LABEL = {
	availability: "Disponibilité",
	transaction: "Transaction",
	dashboard: "Tableau de bord",
};

const editorOpen = ref(false);
</script>

<template>
	<div class="cp-context-bar">
		<div class="cp-context-chips">
			<span class="cx-badge cp-context-chip">{{ PAGE_LABEL[context.page] || context.page }}</span>
			<span v-if="context.active_doctype && shareReference" class="cx-badge cp-context-chip">
				{{ context.active_doctype }}<span v-if="context.active_document_name"> · {{ context.active_document_name }}</span>
			</span>
			<button
				v-if="context.active_doctype"
				class="cx-btn cp-edit-context-btn"
				:aria-expanded="editorOpen"
				@click="editorOpen = !editorOpen"
			>
				Modifier le contexte
			</button>
		</div>

		<!--
			Only one real toggle here: whether the currently open document
			is shared with the next message. Selected item/serial codes and
			"documents ajoutés" from the original spec's mockup aren't wired
			to any real selection state in this pass (no source produces
			them yet) — no fake checkboxes for controls that would do
			nothing. See docs/frontend/copilot-panel.md.
		-->
		<div v-if="editorOpen && context.active_doctype" class="cp-context-editor">
			<label class="cx-check">
				<input
					type="checkbox"
					:checked="shareReference"
					@change="emit('update:shareReference', $event.target.checked)"
				/>
				<span class="cx-text-body"
					>Document actuel ({{ context.active_doctype }}{{
						context.active_document_name ? " " + context.active_document_name : ""
					}})</span
				>
			</label>
		</div>
	</div>
</template>

<style scoped>
.cp-context-bar {
	padding: var(--space-2) var(--space-4);
	border-bottom: 1px solid var(--cortex-border);
	background: var(--cortex-surface-subtle);
}
.cp-context-chips {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: var(--space-2);
}
.cp-context-chip {
	background: var(--cortex-surface);
	border: 1px solid var(--cortex-border);
	color: var(--cortex-text-secondary);
}
.cp-edit-context-btn {
	font-size: 11.5px;
	padding: 2px var(--space-2);
	margin-left: auto;
}
.cp-context-editor {
	margin-top: var(--space-2);
	padding-top: var(--space-2);
	border-top: 1px solid var(--cortex-border);
}
</style>
