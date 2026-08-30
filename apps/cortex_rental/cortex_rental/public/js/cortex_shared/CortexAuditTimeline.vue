<script setup>
import { ref } from "vue";

// Placeholder per the design-system scope: renders a two-mode timeline
// (operational sentence vs. technical detail) from data the caller
// already has — it does not fetch Audit Event records itself. No
// live Audit Event query is wired in this pass.
//
// events: [{
//   timestamp, actorLabel, text,
//   technical?: { requestId, actorId, policyVersion, payloadDiff }
// }]
defineProps({
	events: { type: Array, required: true },
});

const mode = ref("operational");
</script>

<template>
	<div class="cx-audit-timeline">
		<div class="cx-flex cx-justify-between cx-items-center" style="margin-bottom: var(--space-3)">
			<span class="cx-text-label">Historique</span>
			<div class="cx-view-toggle" role="group" aria-label="Mode d'affichage de l'historique">
				<button
					class="cx-btn"
					:class="{ 'cx-btn-active': mode === 'operational' }"
					@click="mode = 'operational'"
				>
					Opérationnel
				</button>
				<button class="cx-btn" :class="{ 'cx-btn-active': mode === 'technical' }" @click="mode = 'technical'">
					Technique
				</button>
			</div>
		</div>

		<ol class="cx-audit-list">
			<li v-for="(event, i) in events" :key="i" class="cx-audit-item">
				<span class="cx-text-mono cx-audit-time">{{ event.timestamp }}</span>
				<div>
					<p class="cx-text-body" style="margin: 0">
						<strong>{{ event.actorLabel }}</strong> · {{ event.text }}
					</p>
					<dl v-if="mode === 'technical' && event.technical" class="cx-audit-technical cx-text-mono">
						<template v-for="(value, key) in event.technical" :key="key">
							<dt>{{ key }}</dt>
							<dd>{{ value }}</dd>
						</template>
					</dl>
				</div>
			</li>
		</ol>
	</div>
</template>

<style scoped>
.cx-view-toggle {
	display: inline-flex;
	border: 1px solid var(--cortex-border);
	border-radius: var(--radius-md);
	overflow: hidden;
}
.cx-view-toggle .cx-btn {
	border: none;
	border-radius: 0;
}
.cx-view-toggle .cx-btn-active {
	background: var(--cortex-primary-600);
	color: var(--cortex-inverse);
}
.cx-audit-list {
	list-style: none;
	margin: 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-3);
}
.cx-audit-item {
	display: flex;
	gap: var(--space-3);
	padding-bottom: var(--space-3);
	border-bottom: 1px solid var(--cortex-border);
}
.cx-audit-time {
	flex-shrink: 0;
	color: var(--cortex-text-muted);
	width: 64px;
}
.cx-audit-technical {
	margin: var(--space-2) 0 0;
	font-size: 11.5px;
	color: var(--cortex-text-muted);
	display: grid;
	grid-template-columns: max-content 1fr;
	gap: 2px var(--space-2);
}
.cx-audit-technical dt {
	font-weight: 600;
}
.cx-audit-technical dd {
	margin: 0;
	word-break: break-all;
}
</style>
