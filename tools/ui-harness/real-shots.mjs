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
if (scenario === "onboarding") {
	// Onboarding réel d'un propriétaire : on remet son onboarding « à faire » (puis on le restaure) et on le parcourt.
	const { execSync } = await import("child_process");
	const py = (code) => { fs.writeFileSync("/tmp/q.py", `import os,json\nos.chdir('/home/frappe/frappe-bench/sites')\nimport frappe\nfrappe.init(site='cortex.localhost',sites_path='.');frappe.connect();frappe.set_user('Administrator')\n${code}\nfrappe.db.commit()`); execSync("docker cp /tmp/q.py fb:/tmp/q.py"); return JSON.parse(execSync("docker exec -u frappe fb bash -c 'cd /home/frappe/frappe-bench/sites && ../env/bin/python /tmp/q.py'").toString().trim().split("\n").pop()); };
	// Sur ce site de simulation le propriétaire n'a pas d'onboarding : on en crée un pour l'essai (et on le retire ensuite).
	const saved = py("from cortex_rental.services import tenant_provisioning as tp\nC='Studio Lumière'\nif frappe.db.exists('Cortex Onboarding',C):\n    d=frappe.get_doc('Cortex Onboarding',C)\n    print(json.dumps({k:d.get(k) for k in ['status','profile_done','team_done','catalog_done','policies_done','owner_done','first_rental_done','skipped_steps']}))\nelse:\n    tp.ensure_onboarding(C,'kael@studio-lumiere.test')\n    print(json.dumps(None))");
	py("frappe.db.set_value('Cortex Onboarding','Studio Lumière',{'status':'In Progress','profile_done':0,'team_done':0,'catalog_done':0,'policies_done':0,'owner_done':0,'first_rental_done':0,'skipped_steps':''})\nprint(json.dumps(True))");
	// Le logo est obligatoire à cette étape : on en pose un de test (retiré ensuite).
	execSync("docker cp /tmp/test-logo.png fb:/tmp/test-logo.png");
	py("c=open('/tmp/test-logo.png','rb').read()\nf=frappe.get_doc({'doctype':'File','file_name':'logo-essai.png','content':c,'is_private':0}).insert(ignore_permissions=True)\nfrappe.db.set_value('Company','Studio Lumière','company_logo',f.file_url)\nprint(json.dumps(f.name))");
	try {
		await go("/app/cortex-setup", 2500);
		await page.screenshot({ path: `${OUT}/onboarding-1-etape.png` });
		console.log("étapes :", JSON.stringify(await page.locator(".cx-onb-step").allInnerTexts()));
		const saveBtn = page.locator(".cx-onb-foot .btn-primary").first();
		console.log("bouton principal :", await saveBtn.innerText().catch(() => "(aucun)"));
		const fields = await page.locator(".cx-onb-content input:visible, .cx-onb-content select:visible, .cx-onb-content textarea:visible").evaluateAll((els) => els.map((e) => `${e.tagName}#${e.id || e.name} value=${(e.value || "").slice(0, 20)}`));
		console.log("champs :", JSON.stringify(fields));
		for (const [id, v] of [["cx-addr", "123 rue Principale"], ["cx-city", "Montréal"], ["cx-state", "QC"], ["cx-zip", "H2X 1Y4"], ["cx-phone", "514 555 0100"], ["cx-mail", "info@studio-lumiere.test"]]) await page.fill(`#${id}`, v);
		await saveBtn.click();
		const flash = await page.waitForSelector(".cx-onb-saved", { timeout: 15000 }).then(() => true).catch(() => false);
		console.log("« Enregistré » apparaît après l'enregistrement :", flash);
		await page.waitForTimeout(250);
		await page.screenshot({ path: `${OUT}/onboarding-2-enregistre.png` });
		const pops = await page.locator(".cx-onb-step.pop").count();
		console.log("coche animée sur l'étape terminée (classe pop) :", pops >= 1, "| étape suivante :", (await page.locator(".cx-onb-step.on").innerText().catch(() => "")).replace(/\s+/g, " "));
		await page.waitForTimeout(2600);
		console.log("« Enregistré » disparaît ensuite :", (await page.locator(".cx-onb-saved").count()) === 0);
		await page.screenshot({ path: `${OUT}/onboarding-3-suite.png` });
	} finally {
		py("frappe.db.set_value('Company','Studio Lumière','company_logo','')\nfor n in frappe.get_all('File',filters={'file_name':'logo-essai.png'},pluck='name'): frappe.delete_doc('File',n,force=1,ignore_permissions=True)\nprint(json.dumps(True))");
		if (process.env.KEEP_ONB !== "1") py(saved ? `frappe.db.set_value('Cortex Onboarding','Studio Lumière',${JSON.stringify(saved).replace(/null/g, "None")})\nprint(json.dumps(True))` : "frappe.delete_doc('Cortex Onboarding','Studio Lumière',force=1,ignore_permissions=True)\nprint(json.dumps(True))");
	}
}
console.log("erreurs JS :", page.errors.length ? page.errors.join(" | ") : "aucune");
await browser.close();
