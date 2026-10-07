// Tests Node (sans navigateur) de la saisie vocale : `node --test cortex_rental/tests/js`.
import test from "node:test";
import assert from "node:assert/strict";
import {
	checkVoiceSupport,
	createVoiceInput,
	explainVoiceError,
	queryMicrophonePermission,
} from "../../public/js/cortex_shared/cortexVoice.js";

class FakeRec {
	static last = null;
	static startError = null;
	constructor() {
		FakeRec.last = this;
		this.started = false;
	}
	start() {
		if (FakeRec.startError) throw FakeRec.startError;
		this.started = true;
		queueMicrotask(() => this.onstart && this.onstart());
	}
	stop() {
		this.started = false;
		this.onend && this.onend();
	}
	abort() {
		this.stop();
	}
}
const results = (...items) => ({
	resultIndex: 0,
	results: items.map(([transcript, isFinal]) => Object.assign([{ transcript }], { isFinal })),
});
const env = (extra = {}) => ({ webkitSpeechRecognition: FakeRec, isSecureContext: true, ...extra });
const tick = () => new Promise((r) => setTimeout(r, 0));

test("navigateur sans reconnaissance vocale : indisponibilité dite avant le clic", () => {
	const r = checkVoiceSupport({ isSecureContext: true });
	assert.equal(r.ok, false);
	assert.equal(r.code, "unsupported-browser");
	assert.match(r.message, /pas prise en charge/);
});

test("connexion non sécurisée et politique du serveur sont distinguées", () => {
	assert.equal(checkVoiceSupport(env({ isSecureContext: false })).code, "insecure-context");
	const blocked = env({ document: { permissionsPolicy: { allowsFeature: () => false } } });
	assert.equal(checkVoiceSupport(blocked).code, "blocked-by-policy");
	const allowed = env({ document: { permissionsPolicy: { allowsFeature: () => true } } });
	assert.equal(checkVoiceSupport(allowed).ok, true);
});

test("chaque code d'erreur du navigateur a un message français actionnable", () => {
	for (const code of ["not-allowed", "service-not-allowed", "no-speech", "audio-capture", "network", "language-not-supported"]) {
		assert.ok(explainVoiceError(code).length > 20, code);
	}
	assert.equal(explainVoiceError("aborted"), null);
	assert.match(explainVoiceError("bizarre"), /bizarre/);
});

test("dictée : provisoire puis définitif, états et arrêt", async () => {
	const states = [];
	const finals = [];
	const interims = [];
	const v = createVoiceInput({
		env: env(),
		onState: (s) => states.push(s),
		onInterim: (t) => interims.push(t),
		onTranscript: (t) => finals.push(t),
	});
	assert.equal(v.start(), true);
	await tick();
	assert.deepEqual(states, ["starting", "listening"]);
	assert.equal(FakeRec.last.lang, "fr-CA");
	FakeRec.last.onresult(results(["bonjour", false]));
	FakeRec.last.onresult(results(["bonjour Cortex", true]));
	assert.deepEqual(finals, ["bonjour Cortex"]);
	assert.equal(interims[0], "bonjour");
	v.stop();
	assert.equal(states.at(-1), "idle");
});

test("permission refusée : message de réglage du site, pas d'échec silencieux", async () => {
	const errors = [];
	const v = createVoiceInput({ env: env(), onError: (e) => errors.push(e) });
	v.start();
	await tick();
	FakeRec.last.onerror({ error: "not-allowed" });
	assert.equal(errors[0].code, "not-allowed");
	assert.match(errors[0].message, /refusé/);
});

test("arrêt volontaire : aucune erreur affichée", async () => {
	const errors = [];
	const v = createVoiceInput({ env: env(), onError: (e) => errors.push(e) });
	v.start();
	await tick();
	v.stop();
	FakeRec.last.onerror({ error: "aborted" });
	assert.deepEqual(errors, []);
});

test("fr-CA non pris en charge : une seule reprise en fr-FR, puis message", async () => {
	const errors = [];
	const v = createVoiceInput({ env: env(), onError: (e) => errors.push(e) });
	v.start();
	await tick();
	const first = FakeRec.last;
	first.onerror({ error: "language-not-supported" });
	const second = FakeRec.last;
	assert.notEqual(first, second);
	assert.equal(second.lang, "fr-FR");
	assert.deepEqual(errors, []);
	second.onerror({ error: "language-not-supported" });
	assert.equal(errors[0].code, "language-not-supported");
});

test("démarrage impossible : signalé, état revient à inactif", () => {
	FakeRec.startError = Object.assign(new Error("x"), { name: "NotAllowedError" });
	const errors = [];
	const states = [];
	const v = createVoiceInput({ env: env(), onError: (e) => errors.push(e), onState: (s) => states.push(s) });
	assert.equal(v.start(), false);
	assert.equal(errors[0].code, "not-allowed");
	assert.equal(states.at(-1), "idle");
	FakeRec.startError = null;
});

test("navigateur non pris en charge : start() signale l'erreur sans rien lancer", () => {
	const errors = [];
	const v = createVoiceInput({ env: { isSecureContext: true }, onError: (e) => errors.push(e) });
	assert.equal(v.start(), false);
	assert.equal(errors[0].code, "unsupported-browser");
});

test("état du microphone : refusé lu, API absente = inconnu", async () => {
	const denied = { navigator: { permissions: { query: async () => ({ state: "denied" }) } } };
	assert.equal(await queryMicrophonePermission(denied), "denied");
	assert.equal(await queryMicrophonePermission({ navigator: {} }), "unknown");
});
