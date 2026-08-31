<script setup>
import { toastState, toast } from "./toastBus.js";
</script>

<template>
	<div class="cx-toast-container" aria-live="polite" aria-atomic="true">
		<transition-group name="cx-toast">
			<div
				v-for="item in toastState.toasts"
				:key="item.id"
				class="cx-toast-item"
				:class="`cx-toast-${item.type}`"
				role="alert"
			>
				<span class="cx-toast-icon" aria-hidden="true">
					{{ item.type === 'success' ? '✓' : item.type === 'warning' ? '⚠️' : item.type === 'error' ? '❌' : 'ℹ️' }}
				</span>
				<div class="cx-toast-content">
					<div v-if="item.title" class="cx-toast-title">{{ item.title }}</div>
					<div class="cx-toast-message">{{ item.message }}</div>
				</div>
				<button
					class="cx-toast-close"
					aria-label="Fermer la notification"
					@click="toast.dismiss(item.id)"
				>
					×
				</button>
			</div>
		</transition-group>
	</div>
</template>

<style scoped>
.cx-toast-container {
	position: fixed;
	top: 20px;
	right: 20px;
	z-index: 9999;
	display: flex;
	flex-direction: column;
	gap: 10px;
	pointer-events: none;
	max-width: 400px;
	width: calc(100vw - 40px);
}

.cx-toast-item {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	background: #ffffff;
	border-radius: 8px;
	padding: 12px 16px;
	box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.06);
	pointer-events: auto;
	border-left: 4px solid #94a3b8;
	font-family: var(--font-family-sans, sans-serif);
	font-size: 13px;
	line-height: 1.45;
}

.cx-toast-success {
	border-left-color: #22c55e;
	background: #f0fdf4;
	color: #14532d;
}

.cx-toast-warning {
	border-left-color: #f59e0b;
	background: #fffbeb;
	color: #78350f;
}

.cx-toast-error {
	border-left-color: #ef4444;
	background: #fef2f2;
	color: #7f1d1d;
}

.cx-toast-info {
	border-left-color: #3b82f6;
	background: #eff6ff;
	color: #1e3a8a;
}

.cx-toast-icon {
	font-weight: 700;
	font-size: 15px;
	line-height: 1.2;
}

.cx-toast-content {
	flex: 1;
}

.cx-toast-title {
	font-weight: 700;
	margin-bottom: 2px;
}

.cx-toast-close {
	background: transparent;
	border: none;
	font-size: 18px;
	line-height: 1;
	color: currentColor;
	opacity: 0.6;
	cursor: pointer;
	padding: 0;
}

.cx-toast-close:hover {
	opacity: 1;
}

/* Animations */
.cx-toast-enter-active,
.cx-toast-leave-active {
	transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.cx-toast-enter-from {
	opacity: 0;
	transform: translateX(40px) scale(0.95);
}

.cx-toast-leave-to {
	opacity: 0;
	transform: translateY(-20px) scale(0.95);
}
</style>
