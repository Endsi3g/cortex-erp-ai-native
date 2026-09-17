<script setup>
import { onMounted, onBeforeUnmount, watch } from "vue";
import { ICONS } from "./CortexIcons.js";

const props = defineProps({
	open: { type: Boolean, default: false },
	title: { type: String, default: "" },
	subtitle: { type: String, default: "" },
	width: { type: String, default: "540px" },
});

const emit = defineEmits(["close"]);

function onKeydown(e) {
	if (e.key === "Escape" && props.open) {
		emit("close");
	}
}

watch(
	() => props.open,
	(isOpen) => {
		if (isOpen) {
			document.body.style.overflow = "hidden";
		} else {
			document.body.style.overflow = "";
		}
	}
);

onMounted(() => {
	window.addEventListener("keydown", onKeydown);
});

onBeforeUnmount(() => {
	window.removeEventListener("keydown", onKeydown);
	document.body.style.overflow = "";
});
</script>

<template>
	<Teleport to="body">
		<transition name="cx-slideover-fade">
			<div v-if="open" class="cx-slideover-overlay" @click.self="$emit('close')">
				<div
					class="cx-slideover-panel"
					:style="{ width: width, maxWidth: '100vw' }"
					role="dialog"
					aria-modal="true"
					:aria-label="title"
				>
					<header class="cx-slideover-header">
						<div class="cx-slideover-title-wrap">
							<h3 class="cx-slideover-title">{{ title }}</h3>
							<p v-if="subtitle" class="cx-slideover-subtitle">{{ subtitle }}</p>
						</div>
						<button
							type="button"
							class="cx-btn cx-btn-ghost cx-slideover-close"
							aria-label="Fermer (Échap)"
							title="Fermer (Échap)"
							@click="$emit('close')"
						>
							<span class="cx-icon-sm" v-html="ICONS.x"></span>
						</button>
					</header>

					<div class="cx-slideover-body">
						<slot />
					</div>

					<footer v-if="$slots.footer" class="cx-slideover-footer">
						<slot name="footer" />
					</footer>
				</div>
			</div>
		</transition>
	</Teleport>
</template>

<style scoped>
.cx-slideover-overlay {
	position: fixed;
	inset: 0;
	background: rgba(15, 23, 42, 0.4);
	backdrop-filter: blur(2px);
	z-index: 999;
	display: flex;
	justify-content: flex-end;
}

.cx-slideover-panel {
	background: var(--cortex-surface);
	height: 100%;
	display: flex;
	flex-direction: column;
	box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
	border-left: 1px solid var(--cortex-border);
	animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideIn {
	from {
		transform: translateX(100%);
	}
	to {
		transform: translateX(0);
	}
}

.cx-slideover-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	padding: var(--space-4) var(--space-5);
	border-bottom: 1px solid var(--cortex-border);
	background: var(--cortex-surface);
	flex-shrink: 0;
}

.cx-slideover-title-wrap {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.cx-slideover-title {
	font-size: 15px;
	font-weight: 600;
	color: var(--cortex-text-primary);
	margin: 0;
}

.cx-slideover-subtitle {
	font-size: 12px;
	color: var(--cortex-text-muted);
	margin: 0;
}

.cx-slideover-close {
	padding: 4px;
	color: var(--cortex-text-muted);
}
.cx-slideover-close:hover {
	color: var(--cortex-text-primary);
}

.cx-slideover-body {
	flex: 1;
	overflow-y: auto;
	padding: var(--space-5);
}

.cx-slideover-footer {
	padding: var(--space-3) var(--space-5);
	border-top: 1px solid var(--cortex-border);
	background: var(--cortex-surface-muted);
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: var(--space-2);
	flex-shrink: 0;
}

/* Transitions */
.cx-slideover-fade-enter-active,
.cx-slideover-fade-leave-active {
	transition: opacity 0.2s ease;
}

.cx-slideover-fade-enter-from,
.cx-slideover-fade-leave-to {
	opacity: 0;
}
</style>
