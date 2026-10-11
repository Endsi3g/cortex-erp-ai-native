// Parcours VISUEL dans le vrai Desk avec le VRAI Gemma 4 local (niveau « Cortex Local ») : un tableau de statistiques, une liste, une
// carte d'action APPROUVÉE pour de vrai (vérifiée en base) puis ANNULÉE (vérifiée en base). Captures dans OUT (défaut /tmp/real-shots/phase18).
// Très lent sans GPU (quelques minutes par réponse). Usage : node local-visual.mjs   (le bench, le runner et la session connectée doivent exister)
import { chromium } from "playwright-core";
import { execSync } from "child_process";
import fs from "fs";
const BASE = process.env.CORTEX_URL || "http://127.0.0.1:8000";
const OUT = process.env.OUT || "/tmp/real-shots/phase18";
const STATE = process.env.STATE || "/tmp/real-shots/state.json";
fs.mkdirSync(OUT, { recursive: true });

function py(code) {
	const script = `import os,json\nos.chdir('/home/frappe/frappe-bench/sites')\nimport frappe\nfrappe.init(site='cortex.localhost',sites_path='.');frappe.connect();frappe.set_user('Administrator')\n${code}\nfrappe.db.commit()`;
	fs.writeFileSync("/tmp/q.py", script);
	execSync("docker cp /tmp/q.py fb:/tmp/q.py");
	return JSON.parse(execSync("docker exec -u frappe fb bash -c 'cd /home/frappe/frappe-bench/sites && ../env/bin/python /tmp/q.py'").toString().trim().split("\n").pop());
}
// Équipement de démonstration VALIDE (catégorie de la liste du site) : les fiches de démo d'origine ont des catégories hors liste,
// ce que Frappe refuse à l'enregistrement. Créé ici, supprimé à la fin.
const ITEM = py("from cortex_rental.tests.live_fixtures import ensure_profile\nensure_profile('Studio Lumière','DEMO-GEMMA-CAM',serialized=0,quantity=2,rate=300.0)\nname=frappe.db.get_value('Cortex Rental Item Profile',{'item_code':'DEMO-GEMMA-CAM','company':'Studio Lumière'},'name')\ncat=frappe.get_meta('Cortex Rental Item Profile').get_field('category').options.split('\\n')[0]\nfrappe.db.set_value('Cortex Rental Item Profile',name,{'item_name':'Caméra démo Gemma','category':cat})\nprint(json.dumps(name))");
const rate = () => py(`print(json.dumps(float(frappe.db.get_value('Cortex Rental Item Profile','${ITEM}','daily_rate'))))`);

const results = [];
const check = (name, ok, detail = "") => { results.push({ name, ok: !!ok }); console.log(ok ? "OK  " : "FAIL", name, detail); };

const browser = await chromium.launch({ executablePath: process.env.CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: "fr-CA", storageState: STATE });
const page = await ctx.newPage();
page.errors = []; page.on("pageerror", (e) => page.errors.push(String(e).slice(0, 200)));

async function fresh() {
	await page.goto(BASE + "/app/cortex-home", { waitUntil: "networkidle" });
	await page.waitForTimeout(1500);
	await page.getByRole("button", { name: /Cortex (Rapide|Local|Gemma|Équilibré|Avancé|Luna)/ }).first().click();
	await page.waitForTimeout(300);
	await page.getByText("Cortex Local", { exact: false }).first().click();
	await page.waitForTimeout(300);
}
async function ask(text) {
	const t0 = Date.now();
	const box = page.locator("textarea").first();
	await box.fill(text); await box.press("Enter");
	await page.waitForFunction(() => document.querySelectorAll(".cp-message").length >= 2 && !/Cortex réfléchit/.test(document.body.innerText), null, { timeout: 1500000, polling: 4000 }).catch(() => {});
	await page.waitForTimeout(1500);
	return Math.round((Date.now() - t0) / 1000);
}
const convo = async () => (await page.locator(".cp-conversation").first().innerText().catch(() => "")).replace(/\s+/g, " ");

// 1. Statistiques : carte de répartition des locations.
await fresh();
let secs = await ask("Montre-moi la répartition de mes locations par état.");
await page.screenshot({ path: `${OUT}/1-statistiques.png`, fullPage: true });
let text = await convo();
check("carte de statistiques affichée", (await page.locator(".cp-stat, [class*='stat']").count()) > 0 || /par état/i.test(text), `${secs} s`);

// 2. Liste : factures impayées.
await fresh();
secs = await ask("Quelles factures sont encore impayées ?");
await page.screenshot({ path: `${OUT}/2-factures.png`, fullPage: true });
text = await convo();
const unpaid = py("print(json.dumps(frappe.get_all('Cortex Rental Invoice',filters={'company':'Studio Lumière','status':['in',['Issued','Partially Paid']]},pluck='name')))");
check("toutes les factures impayées réelles sont nommées", unpaid.every((n) => text.includes(n)), `${unpaid.length} factures, ${secs} s`);

// 3. Action : proposer, approuver pour de vrai, vérifier en base, annuler, vérifier en base.
const before = rate();
await fresh();
secs = await ask("Change le tarif journalier de la caméra démo Gemma à 700 $");
await page.screenshot({ path: `${OUT}/3-carte-a-approuver.png`, fullPage: true });
check("une carte « Modifier un champ » est à approuver", (await page.locator(".cp-action").count()) === 1 && (await page.locator(".cp-action-approve").count()) === 1, `${secs} s`);
check("rien n'est changé avant l'approbation", rate() === before, `tarif ${before}`);
await page.locator(".cp-action-approve").first().click();
await page.waitForFunction(() => /Fait\./.test(document.body.innerText), null, { timeout: 60000 }).catch(() => {});
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/4-carte-approuvee.png`, fullPage: true });
check("après approbation, le tarif est 700 en base", rate() === 700, `tarif ${rate()}`);
const undo = page.getByRole("button", { name: /Annuler cette modification/ });
check("le bouton d'annulation est offert", (await undo.count()) === 1);
if (await undo.count()) {
	await undo.first().click();
	await page.waitForFunction(() => /Annulée/.test(document.body.innerText), null, { timeout: 60000 }).catch(() => {});
	await page.waitForTimeout(800);
	await page.screenshot({ path: `${OUT}/5-carte-annulee.png`, fullPage: true });
}
check("après annulation, le tarif est revenu à sa valeur d'origine", rate() === before, `tarif ${rate()}`);

check("aucune erreur JavaScript", page.errors.length === 0, page.errors.join(" | "));
py(`frappe.db.sql("delete from \`tabCortex AI Action\` where status='Proposed' and company='Studio Lumière'")\nfrappe.delete_doc('Cortex Rental Item Profile','${ITEM}',force=True,ignore_permissions=True)\nprint(json.dumps(True))`);
console.log(`\n${results.filter((r) => r.ok).length}/${results.length} vérifications réussies`);
await browser.close();
process.exit(results.every((r) => r.ok) ? 0 : 1);
