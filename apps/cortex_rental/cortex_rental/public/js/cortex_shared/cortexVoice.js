// Saisie vocale de Cortex : reconnaissance native du navigateur (Web Speech API), sans service propre à Cortex.
//
// Règles d'honnêteté :
// - on ne dit jamais « ça marche » avant d'avoir une réponse du navigateur; l'indisponibilité est dite avant
//   le clic (navigateur, connexion non sécurisée, politique du serveur) ou après l'échec (permission, microphone,
//   réseau, service désactivé) avec la mesure à prendre;
// - le navigateur (et selon lui un service du fournisseur du navigateur) traite l'audio : Cortex ne le reçoit ni ne
//   l'enregistre, seul le texte reconnu arrive dans la zone de saisie, que la personne relit avant d'envoyer.
// Module sans dépendance (testable sous Node : `tests/js/cortexVoice.test.mjs`).

export const VOICE_LANG = "fr-CA";
const FALLBACK_LANG = "fr-FR";

export const VOICE_PRIVACY_NOTE =
	"Le navigateur traite l'audio pour le convertir en texte ; Cortex ne reçoit que le texte, que vous relisez avant d'envoyer.";

const MESSAGES = {
	"unsupported-browser":
		"La saisie vocale n'est pas prise en charge par ce navigateur. Utilisez Chrome, Edge ou Safari, ou écrivez votre demande.",
	"insecure-context":
		"La saisie vocale exige une connexion sécurisée (HTTPS). Écrivez votre demande ou ouvrez Cortex par son adresse sécurisée.",
	"blocked-by-policy":
		"Le microphone est bloqué par la configuration de cette page ou du serveur (politique d'autorisations). Prévenez l'administrateur ; en attendant, écrivez votre demande.",
	"permission-denied":
		"L'accès au microphone est refusé. Autorisez-le dans les réglages du site (cadenas à gauche de l'adresse), puis réessayez.",
	"not-allowed":
		"L'accès au microphone est refusé. Autorisez-le dans les réglages du site (cadenas à gauche de l'adresse), puis réessayez.",
	"service-not-allowed":
		"Le service de reconnaissance vocale est désactivé ou refusé par le navigateur ou l'appareil (sur iPhone : Réglages › Général › Clavier › Activer la dictée).",
	"no-speech": "Aucune voix détectée. Parlez plus près du microphone et réessayez.",
	"audio-capture":
		"Aucun microphone n'a été trouvé. Branchez-en un, ou vérifiez qu'un autre programme ne l'utilise pas.",
	network:
		"Le service de reconnaissance vocale du navigateur est injoignable (connexion Internet, ou navigateur qui bloque ce service). Écrivez votre demande.",
	"language-not-supported": "Le français n'est pas pris en charge par la reconnaissance vocale de ce navigateur.",
};

// Retourne le message français d'un code d'erreur ; `null` quand l'arrêt est volontaire (rien à afficher).
export function explainVoiceError(code) {
	if (code === "aborted") return null;
	return MESSAGES[code] || `La saisie vocale a échoué (code : ${code || "inconnu"}). Écrivez votre demande.`;
}

export function recognitionClass(env = globalThis) {
	return env.SpeechRecognition || env.webkitSpeechRecognition || null;
}

function policyAllowsMicrophone(env) {
	const doc = env.document;
	const policy = doc && (doc.permissionsPolicy || doc.featurePolicy);
	if (!policy || typeof policy.allowsFeature !== "function") return true; // navigateur sans cette API : le clic tranchera
	try {
		return policy.allowsFeature("microphone") !== false;
	} catch (e) {
		return true;
	}
}

// Vérification immédiate, avant tout clic : { ok, code, message }.
export function checkVoiceSupport(env = globalThis) {
	if (!recognitionClass(env)) return { ok: false, code: "unsupported-browser", message: MESSAGES["unsupported-browser"] };
	if (env.isSecureContext === false) return { ok: false, code: "insecure-context", message: MESSAGES["insecure-context"] };
	if (!policyAllowsMicrophone(env)) return { ok: false, code: "blocked-by-policy", message: MESSAGES["blocked-by-policy"] };
	return { ok: true, code: null, message: "" };
}

// « granted » | « denied » | « prompt » | « unknown » (Safari et Firefox ne savent pas interroger le microphone).
export async function queryMicrophonePermission(env = globalThis) {
	try {
		const status = await env.navigator.permissions.query({ name: "microphone" });
		return status.state || "unknown";
	} catch (e) {
		return "unknown";
	}
}

// Contrôleur d'une session de dictée.
// Callbacks : onState('idle' | 'starting' | 'listening'), onInterim(texte provisoire), onTranscript(texte définitif),
// onError({ code, message }). `start()` retourne false quand la dictée est impossible (l'erreur a été signalée).
export function createVoiceInput({ env = globalThis, lang = VOICE_LANG, onState, onInterim, onTranscript, onError } = {}) {
	let rec = null;
	let state = "idle";
	let userStopped = false;
	let triedFallback = false;
	let currentLang = lang;

	const setState = (next) => {
		state = next;
		if (onState) onState(next);
	};
	const fail = (code) => {
		const message = explainVoiceError(code);
		if (message && onError) onError({ code, message });
	};

	function launch() {
		const Rec = recognitionClass(env);
		rec = new Rec();
		rec.lang = currentLang;
		rec.continuous = false;
		rec.interimResults = true;
		rec.maxAlternatives = 1;
		rec.onstart = () => setState("listening");
		rec.onresult = (evt) => {
			let interim = "";
			let final = "";
			for (let i = evt.resultIndex || 0; i < evt.results.length; i += 1) {
				const alt = evt.results[i][0];
				if (!alt) continue;
				if (evt.results[i].isFinal) final += alt.transcript;
				else interim += alt.transcript;
			}
			if (onInterim) onInterim(interim.trim());
			if (final.trim() && onTranscript) onTranscript(final.trim());
		};
		rec.onerror = (evt) => {
			const code = (evt && evt.error) || "unknown";
			if (code === "aborted" && userStopped) return;
			if (code === "language-not-supported" && !triedFallback && currentLang !== FALLBACK_LANG) {
				triedFallback = true;
				currentLang = FALLBACK_LANG;
				rec.onend = null;
				try {
					launch();
					return;
				} catch (e) {
					// on retombe sur l'erreur d'origine
				}
			}
			fail(code);
		};
		rec.onend = () => {
			if (onInterim) onInterim("");
			setState("idle");
		};
		rec.start();
	}

	return {
		get state() {
			return state;
		},
		start() {
			if (state !== "idle") return false;
			const support = checkVoiceSupport(env);
			if (!support.ok) {
				if (onError) onError({ code: support.code, message: support.message });
				return false;
			}
			userStopped = false;
			triedFallback = false;
			currentLang = lang;
			setState("starting");
			try {
				launch();
			} catch (e) {
				setState("idle");
				fail(e && e.name === "NotAllowedError" ? "not-allowed" : "unknown");
				return false;
			}
			return true;
		},
		stop() {
			userStopped = true;
			if (rec) {
				try {
					rec.stop();
				} catch (e) {
					// déjà arrêtée
				}
			}
			setState("idle");
		},
		abort() {
			userStopped = true;
			if (rec) {
				try {
					rec.abort();
				} catch (e) {
					// déjà arrêtée
				}
			}
			setState("idle");
		},
	};
}
