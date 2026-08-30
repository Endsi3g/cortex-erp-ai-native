// Thin wrapper around the real cortex_rental.api.v1.chat endpoints
// (see apps/cortex_rental/cortex_rental/api/v1/chat.py). Calls the
// actual Frappe backend — which itself talks to MockOnyxChatClient,
// not a real Onyx (see HANDOFF.md) — rather than faking data
// client-side, so this panel is a real integration test of the chat
// gateway contract, not throwaway UI.
//
// Deliberately never sends `company`, `agent`, `model`, or
// `allowed_tool_ids` — those fields don't exist on the request shape
// server-side (schemas/chat_schemas.py rejects them outright), so
// there's nothing to accidentally leak here either.

function call(method, args) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: `cortex_rental.api.v1.chat.${method}`,
			type: method.startsWith("get_") || method === "list_sessions" ? "GET" : "POST",
			args,
			callback(r) {
				resolve(r.message || {});
			},
			error(r) {
				const message =
					(r && r.responseJSON && (r.responseJSON.message || r.responseJSON.exc)) ||
					"Le service de conversation Cortex est indisponible.";
				reject(new Error(message));
			},
		});
	});
}

export function sendMessage(message, context, chatSessionId) {
	return call("send_message", {
		message,
		context: JSON.stringify(context),
		chat_session_id: chatSessionId || undefined,
	});
}

export function listSessions() {
	return call("list_sessions", {});
}

export function getSession(name) {
	return call("get_session", { name });
}

export function pinContext(chatSessionId, contextSnapshotId) {
	return call("pin_context", { chat_session_id: chatSessionId, context_snapshot_id: contextSnapshotId });
}

export function clearContext(chatSessionId) {
	return call("clear_context", { chat_session_id: chatSessionId });
}

// ---------------------------------------------------------------------
// Desk context resolution — real frappe.get_route(), not a guess.
// Recomputed when the panel opens and before each send, not reactively
// on background navigation (disclosed simplification — see
// docs/design-system.md's copilot panel section for why).
// ---------------------------------------------------------------------
const ROUTE_TO_PAGE = {
	"cortex-availability": "availability",
};

export function resolveDeskContext() {
	const route = (typeof frappe !== "undefined" && frappe.get_route && frappe.get_route()) || [];
	const context = {
		page: "dashboard",
		locale: (frappe.boot && frappe.boot.lang === "en" ? "en-CA" : "fr-CA") || "fr-CA",
	};

	if (route[0] === "Form" && route[1] && route[2]) {
		context.active_doctype = route[1];
		context.active_document_name = route[2];
		context.page = route[1] === "Cortex Rental Transaction" ? "transaction" : "dashboard";
	} else if (route[0] && ROUTE_TO_PAGE[route[0]]) {
		context.page = ROUTE_TO_PAGE[route[0]];
	}

	return context;
}
