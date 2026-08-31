// Reactive Toast Event Bus for SaaS-grade notifications
// Lightweight, reactive, zero external dependency.

import { reactive } from "vue";

export const toastState = reactive({
	toasts: [], // array of { id, type: "success"|"warning"|"error"|"info", title, message, duration }
});

let toastIdCounter = 0;

export const toast = {
	show(options) {
		const id = ++toastIdCounter;
		const item = {
			id,
			type: options.type || "info",
			title: options.title || "",
			message: typeof options === "string" ? options : options.message || "",
			duration: options.duration || 4000,
		};

		toastState.toasts.push(item);

		if (item.duration > 0) {
			setTimeout(() => {
				toast.dismiss(id);
			}, item.duration);
		}
		return id;
	},

	success(message, title = "") {
		return toast.show({ type: "success", message, title });
	},

	warning(message, title = "") {
		return toast.show({ type: "warning", message, title });
	},

	error(message, title = "") {
		return toast.show({ type: "error", message, title, duration: 6000 });
	},

	info(message, title = "") {
		return toast.show({ type: "info", message, title });
	},

	dismiss(id) {
		const idx = toastState.toasts.findIndex((t) => t.id === id);
		if (idx !== -1) {
			toastState.toasts.splice(idx, 1);
		}
	},

	clearAll() {
		toastState.toasts.splice(0, toastState.toasts.length);
	},
};
