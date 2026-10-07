#!/usr/bin/env node
// Génère `public/css/cortex-dark.css` : la couche « mode sombre » des écrans propres à Cortex.
//
// Principe : on lit les règles CSS existantes (feuilles de style et blocs <style> des composants Vue) et, pour chaque
// couleur d'un fond, d'un texte ou d'une bordure, on écrit la règle équivalente sous `html[data-theme="dark"]` avec
// une couleur de la palette sombre. Le mode clair n'est jamais modifié (aucune règle claire n'est touchée).
// Le Desk de Frappe (listes, formulaires, menus) gère lui-même son mode sombre via `data-theme="dark"`.
//
// Usage (hors dépôt, dépendances de développement seulement) :
//   NODE_PATH=/chemin/vers/node_modules node bin/generate-dark-theme.mjs
// Les dépendances : `postcss` et `@vue/compiler-sfc`. Le fichier généré est versionné; un test Python vérifie sa palette
// et le contraste (`tests/test_phase8_dark_mode.py`).

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const postcss = require("postcss");
const { parse: parseSfc } = require("@vue/compiler-sfc");

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const PUBLIC = path.join(ROOT, "apps/cortex_rental/cortex_rental/public");
const OUT = path.join(PUBLIC, "css/cortex-dark.css");

const SOURCES = [
	"css/cortex-nav.css",
	"css/cortex-account.css",
	"css/cortex-onboarding.css",
	"css/cortex-dossier.css",
	"css/cortex-a11y.css",
	"js/cortex_home/CortexHome.vue",
	"js/cortex_availability/CortexAvailability.vue",
	...fs
		.readdirSync(path.join(PUBLIC, "js/cortex_copilot"))
		.filter((f) => f.endsWith(".vue"))
		.map((f) => `js/cortex_copilot/${f}`),
];

// ---- Palette sombre (validée en contraste par le test Python) ----
export const PALETTE = {
	bg: "#111113",
	canvas: "#0c0c0e",
	surface: "#18181b",
	subtle: "#1f1f23",
	hover: "#27272a",
	line: "#2e2e33",
	lineStrong: "#52525b",
	text: "#f4f4f5",
	secondary: "#d4d4d8",
	muted: "#a1a1aa",
	inverseBg: "#f4f4f5",
	inverseText: "#09090b",
	greenText: "#6ee7b7",
	amberText: "#fbbf24",
	redText: "#fca5a5",
	blueText: "#93c5fd",
	greenTint: "#0f2a1f",
	amberTint: "#2e2210",
	redTint: "#2d1517",
	blueTint: "#14233a",
	greenLine: "#14532d",
	amberLine: "#5c4310",
	redLine: "#5c2226",
};

function hexToRgb(hex) {
	let h = hex.replace("#", "");
	if (h.length === 3) h = [...h].map((c) => c + c).join("");
	return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}
function hsl([r, g, b]) {
	r /= 255; g /= 255; b /= 255;
	const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
	let h = 0, s = 0;
	if (max !== min) {
		const d = max - min;
		s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
		if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) * 60;
		else if (max === g) h = ((b - r) / d + 2) * 60;
		else h = ((r - g) / d + 4) * 60;
	}
	return { h, s, l };
}
// Teinte d'accent (vert, ambre, rouge, bleu) ou « neutral ». Les gris-bleu « ardoise » (#0f172a, #e2e8f0, #64748b…) sont des
// neutres : un bleu n'est un accent que s'il est vraiment saturé.
function accentHue(h, s) {
	if (s < 0.3) return "neutral";
	if (h >= 75 && h < 170) return s >= 0.4 ? "green" : "neutral";
	if (h >= 20 && h < 60) return s >= 0.4 ? "amber" : "neutral";
	if (h < 20 || h >= 330) return s >= 0.4 ? "red" : "neutral";
	if (h >= 190 && h < 260) return s >= 0.6 ? "blue" : "neutral";
	return "neutral";
}

function mapBackground(hex) {
	const { h, s, l } = hsl(hexToRgb(hex));
	const hue = accentHue(h, s);
	const tint = { green: PALETTE.greenTint, amber: PALETTE.amberTint, red: PALETTE.redTint, blue: PALETTE.blueTint }[hue];
	if (l >= 0.9) {
		if (tint) return tint;
		return l >= 0.995 ? PALETTE.surface : l >= 0.965 ? PALETTE.subtle : PALETTE.hover;
	}
	if (l >= 0.78) return tint || PALETTE.hover;
	if (l <= 0.14 && s < 0.5) return PALETTE.inverseBg; // bouton presque noir : devient clair (texte inversé dans la même règle)
	return null; // couleurs d'accent (vert de marque, rouge d'alerte…) : conservées
}
function mapText(hex) {
	const { h, s, l } = hsl(hexToRgb(hex));
	if (l >= 0.97) return null; // blanc : texte sur fond de couleur, conservé
	const hue = accentHue(h, s);
	if (hue !== "neutral" && l < 0.55) return { green: PALETTE.greenText, amber: PALETTE.amberText, red: PALETTE.redText, blue: PALETTE.blueText }[hue] || null;
	if (l < 0.2) return PALETTE.text;
	if (l < 0.34) return PALETTE.secondary;
	if (l < 0.62) return PALETTE.muted;
	return null;
}
function mapLine(hex) {
	const { h, s, l } = hsl(hexToRgb(hex));
	const hue = accentHue(h, s);
	if (l >= 0.78) {
		if (hue === "green") return PALETTE.greenLine;
		if (hue === "amber") return PALETTE.amberLine;
		if (hue === "red") return PALETTE.redLine;
		return l >= 0.9 ? PALETTE.line : PALETTE.lineStrong;
	}
	return null;
}

const HEX = /#[0-9a-fA-F]{3,8}\b/g;
const isBg = (p) => /^background(-color)?$/.test(p);
const isFg = (p) => p === "color" || p === "fill" || p === "stroke";
const isLine = (p) => /^(border|outline)(-(top|right|bottom|left))?(-color)?$/.test(p);

// Propriétés personnalisées locales d'un composant (ex. --full-bg, --ok, --muted, --line) : le rôle vient du nom.
function customRole(prop) {
	if (/-bg$/.test(prop)) return mapBackground;
	if (/line|border/.test(prop)) return mapLine;
	if (/^--(ok|partial|full|muted|text|danger|warn|success|error)(-|$)/.test(prop)) return mapText;
	return null;
}

function remap(prop, rawValue) {
	// `var(--jeton, #hex)` : le jeton clair ne s'adapterait pas toujours au mode sombre; on remappe la couleur de repli.
	const value = rawValue.replace(/var\(\s*--[\w-]+\s*,\s*(#[0-9a-fA-F]{3,8})\s*\)/g, "$1");
	const mapper = prop.startsWith("--") ? customRole(prop) : isBg(prop) ? mapBackground : isFg(prop) ? mapText : isLine(prop) ? mapLine : null;
	if (!mapper) return null;
	let changed = false;
	const out = value.replace(HEX, (hex) => {
		if (hex.length !== 4 && hex.length !== 7) return hex;
		const mapped = mapper(hex);
		if (!mapped) return hex;
		changed = true;
		return mapped;
	});
	return changed ? out : null;
}

function selectorsFor(rule) {
	return rule.selectors
		.filter((sel) => !/:(?:global|deep)\(/.test(sel))
		.map((sel) => `html[data-theme="dark"] ${sel.replace(/^:root\s*/, "").replace(/^\[data-theme="light"\]\s*/, "")}`.trim());
}

function darkRules(css, from) {
	const root = postcss.parse(css, { from });
	const emitted = [];
	root.walkRules((rule) => {
		if (rule.parent && rule.parent.type === "atrule" && /keyframes/.test(rule.parent.name)) return;
		// Pas de remappage dans une requête « mode clair seulement ».
		const media = rule.parent && rule.parent.type === "atrule" && rule.parent.name === "media" ? rule.parent.params : "";
		if (/prefers-color-scheme:\s*light/.test(media)) return;
		const decls = [];
		let darkButton = false;
		rule.walkDecls((d) => {
			const mapped = remap(d.prop, d.value);
			if (mapped) {
				decls.push({ prop: d.prop, value: mapped, important: d.important });
				if (isBg(d.prop) && mapped.includes(PALETTE.inverseBg)) darkButton = true;
			}
		});
		if (!decls.length) return;
		if (darkButton) {
			// Un bouton sombre devient clair : son texte blanc devient sombre.
			rule.walkDecls("color", (d) => {
				if (/^#(fff|ffffff)$/i.test(d.value.trim())) decls.push({ prop: "color", value: PALETTE.inverseText, important: d.important });
			});
		}
		const selectors = selectorsFor(rule);
		if (!selectors.length) return;
		const body = decls.map((d) => `\t${d.prop}: ${d.value}${d.important ? " !important" : ""};`).join("\n");
		const block = `${selectors.join(",\n")} {\n${body}\n}`;
		emitted.push(media ? `@media ${media} {\n${block.replace(/^/gm, "\t")}\n}` : block);
	});
	return emitted;
}

const header = `/*
 * Cortex — mode sombre (GÉNÉRÉ par bin/generate-dark-theme.mjs : ne pas modifier à la main).
 * S'applique seulement sous html[data-theme="dark"] (choix de la personne : Apparence, dans Mon compte).
 * Le mode clair, par défaut, n'est jamais touché. Premier passage : à valider écran par écran sur un Desk actif.
 */

html[data-theme="dark"] {
	color-scheme: dark;
	--cortex-bg: ${PALETTE.bg};
	--cortex-canvas: ${PALETTE.canvas};
	--cortex-surface: ${PALETTE.surface};
	--cortex-surface-subtle: ${PALETTE.subtle};
	--cortex-surface-hover: ${PALETTE.hover};
	--cortex-border: ${PALETTE.line};
	--cortex-border-strong: #9696a0; /* sert aussi de texte discret : au moins 4,5:1 sur les surfaces sombres */
	--cortex-text: ${PALETTE.text};
	--cortex-text-secondary: ${PALETTE.secondary};
	--cortex-text-muted: ${PALETTE.muted};
	--cortex-text-disabled: #71717a;
	--cortex-inverse: ${PALETTE.inverseText};
	--cx-nav-bg: ${PALETTE.canvas};
	--cx-nav-hover: ${PALETTE.hover};
	--cx-nav-active: #303036;
	--cx-nav-line: ${PALETTE.line};
	--text-muted: ${PALETTE.muted};
	--text-light: ${PALETTE.muted};
	/* Teintes de fond (-50, -100) et textes posés dessus (-700…-900) des familles sémantiques; les fonds pleins (-500, -600) restent. */
	--cortex-emerald-50: ${PALETTE.greenTint}; --cortex-green-50: ${PALETTE.greenTint}; --cortex-success-50: ${PALETTE.greenTint}; --cortex-primary-50: ${PALETTE.greenTint};
	--cortex-emerald-100: #123524; --cortex-green-100: #123524; --cortex-success-100: #123524; --cortex-primary-100: #123524;
	--cortex-emerald-800: ${PALETTE.greenText}; --cortex-emerald-900: ${PALETTE.greenText};
	--cortex-warning-50: ${PALETTE.amberTint}; --cortex-warning-100: #3a2b12; --cortex-warning-800: ${PALETTE.amberText}; --cortex-warning-900: ${PALETTE.amberText};
	--cortex-danger-50: ${PALETTE.redTint}; --cortex-danger-100: #3b1b1e; --cortex-danger-700: ${PALETTE.redText}; --cortex-danger-800: ${PALETTE.redText}; --cortex-danger-900: ${PALETTE.redText};
	--cortex-info-50: ${PALETTE.blueTint}; --cortex-info-100: #172b47; --cortex-info-800: ${PALETTE.blueText}; --cortex-info-900: ${PALETTE.blueText};
}
html[data-theme="dark"] .text-muted,
html[data-theme="dark"] .grid-heading-row .static-area,
html[data-theme="dark"] .breadcrumb .disabled > a,
html[data-theme="dark"] .disabled > a,
html[data-theme="dark"] .fc-day-number {
	color: ${PALETTE.muted} !important;
}
`;

const blocks = [];
for (const rel of SOURCES) {
	const file = path.join(PUBLIC, rel);
	const source = fs.readFileSync(file, "utf8");
	let styles = [source];
	if (rel.endsWith(".vue")) {
		const { descriptor } = parseSfc(source, { filename: file });
		styles = descriptor.styles.map((s) => s.content);
	}
	const rules = styles.flatMap((css) => darkRules(css, file));
	if (rules.length) blocks.push(`/* ---- ${rel} ---- */\n${rules.join("\n")}`);
}
fs.writeFileSync(OUT, `${header}\n${blocks.join("\n\n")}\n`);
console.log(`écrit ${path.relative(ROOT, OUT)} (${blocks.length} sources)`);
