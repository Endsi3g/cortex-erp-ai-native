// Captures du vrai Desk (bench) pour la phase 11 : Assistant plein écran, accueil, onboarding, visite. Usage : node real-shots.mjs <scénario>
import { chromium } from "playwright-core";
import fs from "fs";
const BASE = process.env.CORTEX_URL || "http://127.0.0.1:8000";
const OUT = process.env.OUT || "/tmp/real-shots/phase11";
const STATE = process.env.STATE || "/tmp/real-shots/state.json";
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "fr-CA", storageState: STATE });
const page = await ctx.newPage();
page.errors = []; page.on("pageerror", (e) => page.errors.push(String(e).slice(0, 160)));
const go = async (path, wait = 1800) => { await page.goto(BASE + path, { waitUntil: "networkidle" }); await page.waitForTimeout(wait); };
const theme = (t) => page.evaluate((x) => { document.documentElement.setAttribute("data-theme", x); }, t);
const scenario = process.argv[2] || "assistant";
if (scenario === "assistant") {
	for (const t of ["light", "dark"]) {
		await go("/app/cortex-home"); await theme(t); await page.waitForTimeout(500);
		await page.screenshot({ path: `${OUT}/assistant-accueil-${t}.png` });
		const box = page.locator("textarea").first();
		await box.fill("Change le tarif journalier de TARIF-ZZZ à 175 $."); await box.press("Enter");
		await page.waitForTimeout(6000);
		await page.screenshot({ path: `${OUT}/assistant-conversation-${t}.png` });
		const bar = await page.evaluate(() => [...document.querySelectorAll("header.navbar *")].filter((n) => n.offsetParent !== null && /^(BUTTON|A|INPUT)$/.test(n.tagName)).map((n) => (n.getAttribute("aria-label") || n.title || n.innerText || n.placeholder || "").trim().slice(0, 30)));
		console.log(t, "barre du haut visible :", JSON.stringify(bar), "| fil d'Ariane :", await page.locator("#navbar-breadcrumbs").isVisible());
	}
	await go("/app/cortex-rental-item-profile"); await theme("light");
	await page.screenshot({ path: `${OUT}/autre-page-barre-complete.png` });
	console.log("autre page : fil d'Ariane visible =", await page.locator("#navbar-breadcrumbs").isVisible(), "| recherche visible =", await page.locator("header.navbar .search-bar").isVisible(), "| classe plein écran =", await page.evaluate(() => document.body.classList.contains("cx-ai-fullscreen")));
	await go("/app/cortex-home"); console.log("retour assistant : classe plein écran =", await page.evaluate(() => document.body.classList.contains("cx-ai-fullscreen")));
}
if (scenario === "welcome") {
	// Vraie connexion par le formulaire : le voile apparaît une fois, pas au rechargement, pas dans un autre onglet.
	const fresh = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: "fr-CA" });
	const p = await fresh.newPage();
	p.errors = []; p.on("pageerror", (e) => p.errors.push(String(e).slice(0, 160)));
	await p.goto(BASE + "/login", { waitUntil: "networkidle" });
	await p.fill("#login_email", "kael@studio-lumiere.test");
	await p.fill("#login_password", "Cortex#Test2026!");
	await p.screenshot({ path: `${OUT}/accueil-0-connexion.png` });
	await p.click(".form-login .btn-login");
	await p.waitForSelector(".cx-welcome", { timeout: 30000 }).catch(() => {});
	await p.waitForTimeout(900);
	const seen = await p.locator(".cx-welcome").count();
	console.log("voile affiché après la connexion :", seen === 1, "|", (await p.locator(".cx-welcome").innerText().catch(() => "")).replace(/\s+/g, " "));
	await p.screenshot({ path: `${OUT}/accueil-1-voile.png` });
	await p.waitForTimeout(3200);
	console.log("voile disparu ensuite :", (await p.locator(".cx-welcome").count()) === 0, "| page :", p.url().replace(BASE, ""));
	await p.screenshot({ path: `${OUT}/accueil-2-apres.png` });
	await p.reload({ waitUntil: "networkidle" }); await p.waitForTimeout(1200);
	console.log("pas de voile au rechargement :", (await p.locator(".cx-welcome").count()) === 0);
	const tab2 = await fresh.newPage(); await tab2.goto(BASE + "/app/cortex-home", { waitUntil: "networkidle" }); await tab2.waitForTimeout(1200);
	console.log("pas de voile dans un autre onglet :", (await tab2.locator(".cx-welcome").count()) === 0);
	// Clic : ferme tout de suite.
	await p.evaluate(() => sessionStorage.setItem("cortex_welcome", String(Date.now()))); await p.reload({ waitUntil: "domcontentloaded" });
	await p.waitForSelector(".cx-welcome", { timeout: 30000 }).catch(() => {}); await p.locator(".cx-welcome").click().catch(() => {}); await p.waitForTimeout(800);
	console.log("un clic ferme le voile :", (await p.locator(".cx-welcome").count()) === 0);
	// Drapeau périmé : rien.
	await p.evaluate(() => sessionStorage.setItem("cortex_welcome", String(Date.now() - 120000))); await p.reload({ waitUntil: "networkidle" }); await p.waitForTimeout(800);
	console.log("drapeau périmé : aucun voile :", (await p.locator(".cx-welcome").count()) === 0);
	console.log("erreurs JS (connexion) :", p.errors.length ? p.errors.join(" | ") : "aucune");
	await fresh.close();
}
console.log("erreurs JS :", page.errors.length ? page.errors.join(" | ") : "aucune");
await browser.close();
