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

// First user-facing message of a failed call: `_server_messages` is a JSON list of JSON strings (HTML stripped).
function serverMessage(r) {
	// Frappe passes the parsed body for validation errors (417) and the XHR for other failures.
	const body = r && (r.responseJSON || r);
	if (!body || typeof body !== "object") return "";
	if (body._server_messages) {
		try {
			const first = JSON.parse(body._server_messages)[0];
			const message = typeof first === "string" ? JSON.parse(first).message : "";
			if (message) return String(message).replace(/<[^>]*>/g, "").trim();
		} catch (e) {
			// fall through to the generic message
		}
	}
	return "";
}

function call(method, args) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: `cortex_rental.api.v1.chat.${method}`,
			type: method.startsWith("get_") || method === "list_sessions" ? "GET" : "POST",
			args,
			// Errors are shown in the conversation, not as a second pop-up.
			silent: true,
			callback(r) {
				resolve(r.message || {});
			},
			error(r) {
				reject(new Error(serverMessage(r) || "Le service de conversation Cortex est indisponible."));
			},
		});
	});
}

export function sendMessage(message, context, chatSessionId) {
	// Le serveur répond { data: { chat_session_id, blocks, … }, meta } : on rend la partie utile (sans elle, la réponse
	// de l'assistant s'affichait vide).
	return call("send_message", {
		message,
		context: JSON.stringify(context),
		chat_session_id: chatSessionId || undefined,
	}).then((response) => response.data || response);
}

export function getMessages(name) {
	return call("get_messages", { name });
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
	"cortex-home": "dashboard",
	"query-report": "availability",
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


// Appel générique d'un endpoint Cortex (GET ou POST) : rend la partie utile de la réponse ({ data } ou l'objet lui-même)
// et une erreur en français. À utiliser partout dans l'assistant : un GET appelé en POST échouait sans bruit.
export function apiCall(method, args, type = "GET") {
	return new Promise((resolve, reject) => {
		frappe.call({
			method,
			type,
			args: args || {},
			silent: true,
			callback(r) {
				const message = r.message || {};
				resolve(message.data !== undefined ? message.data : message);
			},
			error(r) {
				reject(new Error(serverMessage(r) || "Le service est indisponible. Réessayez dans un instant."));
			},
		});
	});
}

export function money(value) {
	return new Intl.NumberFormat("fr-CA", { style: "currency", currency: "CAD" }).format(Number(value || 0));
}

// « AAAA-MM-JJTHH:mm » (champ datetime-local) → « AAAA-MM-JJ HH:mm:00 » (format du serveur).
export function toServerDate(local) {
	return local ? `${local.replace("T", " ")}:00` : "";
}
