// Essai RÉEL de Cortex Local (Gemma 4 12B par Docker Model Runner) dans le Desk : le niveau est choisi dans la zone de saisie,
// une vraie question est posée, le vrai modèle choisit un outil réel, la réponse revient. Très lent sur processeur (le premier
// appel traite ~5 000 jetons de consignes et d'outils). Usage : node local-gemma.mjs
import { chromium } from "playwright-core";
import { execSync } from "child_process";
const BASE = "http://127.0.0.1:8000";
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: "fr-CA", storageState: "/tmp/real-shots/state.json" });
const page = await ctx.newPage();
page.errors = []; page.on("pageerror", (e) => page.errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/app/cortex-home", { waitUntil: "networkidle" }); await page.waitForTimeout(2000);
await page.getByRole("button", { name: /Cortex Rapide/ }).click(); await page.waitForTimeout(400);
const menu = await page.locator("body").innerText();
console.log("« Cortex Local » offert :", /Cortex Local/.test(menu), "| « Cortex Gemma » offert :", /Cortex Gemma/.test(menu));
await page.screenshot({ path: "/tmp/real-shots/phase11/local-menu.png" });
await page.getByText("Cortex Local", { exact: false }).first().click(); await page.waitForTimeout(300);
const t0 = Date.now();
const box = page.locator("textarea").first();
await box.fill("Quelles sont mes locations en état devis ? Réponds en une phrase."); await box.press("Enter");
await page.waitForFunction(() => document.querySelectorAll(".cp-message").length >= 2 && !/Cortex réfléchit/.test(document.body.innerText), null, { timeout: 1500000, polling: 5000 }).catch(() => {});
await page.waitForTimeout(2000);
const secs = Math.round((Date.now() - t0) / 1000);
const text = (await page.locator(".cp-conversation").first().innerText().catch(() => "")).replace(/\s+/g, " ");
console.log(`durée : ${secs} s`);
console.log("conversation :", text.slice(0, 700));
await page.screenshot({ path: "/tmp/real-shots/phase11/local-reponse.png", fullPage: true });
console.log("erreurs JS :", page.errors.length ? page.errors.join(" | ") : "aucune");
console.log("journal du runner :", execSync("docker logs dmr 2>&1 | grep -E 'prompt eval|eval time' | tail -4 | cut -c1-200").toString());
await browser.close();
