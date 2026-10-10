// Essais de bout en bout de l'assistant dans un VRAI Desk (bench) : message tapé → modèle (faux Gemini fidèle au protocole)
// → outils réels → cartes → approbation → écriture vérifiée dans la base. Voir tools/bench/README.md.
import { chromium } from "playwright-core";
import { execSync } from "child_process";
import fs from "fs";

const BASE = process.env.CORTEX_URL || "http://127.0.0.1:8000";
const OUT = process.env.OUT || "/tmp/real-shots/e2e";
const STATE = process.env.STATE || "/tmp/real-shots/state.json";
const CHROME = process.env.CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
fs.mkdirSync(OUT, { recursive: true });

// Requête Python dans le conteneur du bench (lecture ou configuration); renvoie du JSON.
function py(code) {
	const script = `import os,json\nos.chdir('/home/frappe/frappe-bench/sites')\nimport frappe\nfrappe.init(site='cortex.localhost',sites_path='.');frappe.connect();frappe.set_user('Administrator')\n${code}\nfrappe.db.commit()`;
	fs.writeFileSync("/tmp/q.py", script);
	execSync("docker cp /tmp/q.py fb:/tmp/q.py");
	return JSON.parse(execSync("docker exec -u frappe fb bash -c 'cd /home/frappe/frappe-bench/sites && ../env/bin/python /tmp/q.py'").toString().trim().split("\n").pop());
}

// Les devis des essais précédents retiennent encore le matériel (72 h) : on libère ces retenues pour repartir d'un parc libre.
py("frappe.db.sql(\"update `tabCortex Rental Transaction` set hold_status='Released' where rental_state='Quote'\")\nprint(json.dumps(True))");

// Une facture d'acompte neuve et ouverte pour le scénario de paiement : devis puis réservation d'un article neuf, par le moteur d'actions.
py(`import json as _j\nfrom cortex_rental.tests.live_fixtures import ensure_profile, ensure_customer\nfrom cortex_rental.services.ai import actions\nU='kael@studio-lumiere.test'; C='Studio Lumière'\ncode='E2E-'+frappe.generate_hash(length=6)\nensure_profile(C, code, serialized=0, quantity=5, rate=200.0)\ncust=ensure_customer('Client essai bout en bout', C)\nfrappe.db.commit(); frappe.set_user(U)\nb=actions.propose('create_quote',{'customer':cust,'starts_at':'2027-03-08 09:00:00','ends_at':'2027-03-10 18:00:00','items':[{'item_code':code,'quantity':1}]},C,U)\nactions.decide(b['action_id'],True,C,U)\nname=_j.loads(frappe.db.get_value('Cortex AI Action',b['action_id'],'result_json'))['id']\nb2=actions.propose('request_reservation',{'rental':name},C,U)\nprint(_j.dumps(actions.decide(b2['action_id'],True,C,U)['ok']))`);

const results = [];
function check(name, ok, detail = "") { results.push({ name, ok, detail }); console.log((ok ? "OK    " : "ECHEC ") + name + (detail ? "  — " + detail : "")); }

const browser = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
async function session() {
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: "fr-CA", storageState: STATE });
	const page = await ctx.newPage();
	page.errors = []; page.on("pageerror", (e) => page.errors.push(String(e).slice(0, 160)));
	await page.goto(BASE + "/app/cortex-home", { waitUntil: "networkidle" }); await page.waitForTimeout(1800);
	return { ctx, page };
}
async function ask(page, text, waitFor = ".cp-action, .cp-stat, .cp-error, [class*=cp-err]", timeout = 40000) {
	const before = await page.locator(".cp-message-assistant, .cp-message").count();
	const box = page.locator("textarea").first();
	await box.fill(text); await box.press("Enter");
	await page.waitForFunction((n) => document.querySelectorAll(".cp-message").length >= n + 2, before, { timeout }).catch(() => {});
	const found = await page.waitForSelector(waitFor, { timeout }).then(() => true).catch(() => false);
	await page.waitForTimeout(1200);
	if (!found) {
		// Rien n'est apparu : on garde la preuve (capture + texte de la conversation) pour comprendre pourquoi.
		await page.screenshot({ path: `${OUT}/echec-${Date.now()}.png`, fullPage: true });
		console.log("   (aucune carte) conversation :", (await lastText(page)).replace(/\s+/g, " ").slice(0, 300));
	}
}
const lastText = (page) => page.locator(".cp-conversation").first().innerText().catch(() => "");

// --- S1 : devis complet (deux articles), approbation, écriture réelle ---------------------------------------------------
{
	const { ctx, page } = await session();
	const n0 = py("print(json.dumps(frappe.db.count('Cortex Rental Transaction',{'rental_state':'Quote'})))");
	await ask(page, "Prépare un devis pour Studio Boréal du 24 au 27 novembre avec deux panneaux LED et un trépied.");
	const card = page.locator(".cp-action").last();
	check("S1 carte de devis affichée", (await card.count()) === 1);
	const rows = await card.locator("tbody tr").count();
	check("S1 deux lignes d'équipement + 4 lignes de totaux", rows === 6, `lignes: ${rows}`);
	check("S1 « Pourquoi cette proposition » présent", (await card.locator("summary").count()) === 1);
	await card.locator("summary").click(); await page.waitForTimeout(300);
	const why = await card.innerText();
	check("S1 raison + données consultées + effets", /Explication de l'assistant/.test(why) && /Données consultées/.test(why) && /Ce qui va se passer/.test(why));
	await page.screenshot({ path: `${OUT}/s1-carte.png`, fullPage: true });
	await card.getByRole("button", { name: /Créer le devis/ }).click();
	await card.locator(".cp-action-badge", { hasText: "Fait" }).waitFor({ timeout: 20000 }).catch(() => {});
	const done = (await card.locator(".cp-action-badge").innerText()).trim();
	check("S1 carte passe à « Fait »", done === "Fait", done);
	const n1 = py("print(json.dumps(frappe.db.count('Cortex Rental Transaction',{'rental_state':'Quote'})))");
	check("S1 un devis réellement créé en base", n1 === n0 + 1, `${n0} → ${n1}`);
	const last = py("r=frappe.get_all('Cortex Rental Transaction',fields=['name','customer'],order_by='creation desc',limit=1)[0]\nitems=frappe.get_all('Cortex Rental Transaction Item',filters={'parent':r.name},pluck='item_code')\nprint(json.dumps({'name':r.name,'items':sorted(items)}))");
	check("S1 les deux articles sont dans le devis", last.items.length === 2, JSON.stringify(last.items));
	await card.getByRole("button", { name: /Ouvrir le devis/ }).click(); await page.waitForTimeout(2500);
	check("S1 le lien ouvre le devis créé", page.url().includes(last.name), page.url().replace(BASE, ""));
	check("S1 aucune erreur JavaScript", page.errors.length === 0, page.errors.join(" | "));
	await ctx.close();
}

// --- S2 : l'état de la carte survit au rechargement de la conversation ----------------------------------------------------
{
	const { ctx, page } = await session();
	await page.locator("button[title*='istor'], button[aria-label*='istor']").first().click(); await page.waitForTimeout(700);
	await page.getByText(/Prépare un devis pour Studio Boréal/).first().click();
	await page.waitForSelector(".cp-action", { timeout: 15000 }).catch(() => {}); await page.waitForTimeout(1000);
	const badges = await page.locator(".cp-action .cp-action-badge").allInnerTexts();
	check("S2 la carte approuvée reste « Fait » après rechargement", badges.includes("Fait"), badges.join(","));
	await ctx.close();
}

// --- S3 : statistiques réelles et flèche vers la source -----------------------------------------------------------------------
{
	const { ctx, page } = await session();
	await ask(page, "Montre-moi la facturation et la situation des locations.", ".cp-stat");
	const stats = await page.locator(".cp-stat").count();
	check("S3 trois cartes de statistiques", stats === 3, `cartes: ${stats}`);
	check("S3 un anneau et des barres", (await page.locator(".cp-donut").count()) === 1 && (await page.locator(".cp-bar").count()) > 0);
	await page.screenshot({ path: `${OUT}/s3-stats.png`, fullPage: true });
	await page.locator(".cp-stat-open").first().click(); await page.waitForTimeout(2500);
	check("S3 la flèche ouvre Finance", page.url().includes("/app/cortex-finance"), page.url().replace(BASE, ""));
	await ctx.close();
}

// --- S4 : paiement sur une vraie facture (celle que la carte montre) -------------------------------------------------------------
{
	const { ctx, page } = await session();
	await ask(page, "Le client vient de payer sa facture par chèque.");
	const card = page.locator(".cp-action").last();
	const text = await card.innerText();
	check("S4 carte de paiement affichée", (await card.count()) === 1 && /Paiement/.test(text));
	const invoice = (text.match(/Facture\s+(\S+)/) || [])[1];
	check("S4 la carte nomme la facture", !!invoice, invoice || "");
	const before = py(`r=frappe.db.get_value('Cortex Rental Invoice','${invoice}',['balance','status'],as_dict=True)\nprint(json.dumps(r))`);
	await page.screenshot({ path: `${OUT}/s4-paiement.png`, fullPage: true });
	await card.getByRole("button", { name: /Enregistrer le paiement/ }).click();
	await card.locator(".cp-action-badge", { hasText: "Fait" }).waitFor({ timeout: 20000 }).catch(() => {});
	const after = py(`r=frappe.db.get_value('Cortex Rental Invoice','${invoice}',['balance','status'],as_dict=True)\np=frappe.get_all('Cortex Rental Payment',filters={'invoice':'${invoice}'},fields=['method','amount','reference'],order_by='creation desc',limit=1)\nprint(json.dumps({'balance':r.balance,'status':r.status,'pay':p[0] if p else None}))`);
	check("S4 le solde de la facture a baissé", after.balance < before.balance, `${before.balance} → ${after.balance} (${after.status})`);
	check("S4 paiement par chèque enregistré", !!after.pay && after.pay.method === "Cheque", JSON.stringify(after.pay));
	await ctx.close();
}

// --- S5 : libérer une retenue ------------------------------------------------------------------------------------------------------
{
	// Le devis le plus récemment modifié doit avoir une retenue active pour que la demande ait un sens.
	const q = py("from cortex_rental.services import holds\nr=frappe.get_all('Cortex Rental Transaction',filters={'rental_state':'Quote'},fields=['name'],order_by='modified desc',limit=1)[0]\nholds.evaluate(frappe.get_doc('Cortex Rental Transaction',r.name))\nprint(json.dumps({'name':r.name,'hold':frappe.db.get_value('Cortex Rental Transaction',r.name,'hold_status')}))");
	check("S5 le devis le plus récent a une retenue active", q.hold === "Active", JSON.stringify(q));
	const { ctx, page } = await session();
	await ask(page, "Libère la retenue du devis le plus récent.");
	const card = page.locator(".cp-action").last();
	check("S5 carte de libération affichée", (await card.count()) === 1 && /Libérer/.test(await card.innerText()));
	await card.getByRole("button", { name: /Libérer la retenue/ }).click();
	await card.locator(".cp-action-badge", { hasText: "Fait" }).waitFor({ timeout: 20000 }).catch(() => {});
	const hold = py(`print(json.dumps(frappe.db.get_value('Cortex Rental Transaction','${q.name}','hold_status')))`);
	check("S5 la retenue est libérée en base", hold === "Released", `${q.name} → ${hold}`);
	await ctx.close();
}

// --- Pannes : le système échoue proprement, en français, sans carte trompeuse ------------------------------------------------------------
const setAI = (fields) => py(`d=frappe.get_doc('Cortex AI Settings')\nfor k,v in ${JSON.stringify(fields)}.items(): d.set(k,v)\nd.save(ignore_permissions=True)\nprint(json.dumps(True))`);
const KEY = "fake-gemini-key";
const reply = async (text) => { const { ctx, page } = await session(); await ask(page, text, ".cp-message-assistant, .cp-error, [class*=error]", 25000); await page.waitForTimeout(3000); /* le texte s'affiche avant les cartes et avis */ const t = (await lastText(page)).replace(/\s+/g, " "); await ctx.close(); return t; };
try {
	setAI({ api_key: "mauvaise-cle" });
	let t = await reply("Bonjour, que peux-tu faire?");
	check("S6 mauvaise clé : message clair en français", /clé API .* refusée/i.test(t) || /clé/i.test(t) && /refus/i.test(t), t.slice(-160));
	setAI({ api_key: KEY });

	t = await reply("Bonjour [panne]");
	check("S6 service indisponible : message clair", /indisponible|temporairement|momentan/i.test(t), t.slice(-160));

	t = await reply("Bonjour [limite]");
	check("S6 limite 429 du fournisseur : relance silencieuse, réponse obtenue", /Je peux consulter/.test(t), t.slice(-160));

	setAI({ model: "gemini-inexistant-1", fallback_model: "gemini-3.8-flash" });
	t = await reply("Bonjour, que peux-tu faire?");
	check("S6 modèle introuvable : le modèle de repli répond", /Je peux consulter/.test(t), t.slice(-160));
	setAI({ model: "gemini-3.8-flash", fallback_model: "" });

	// Plafond de dépense : entre 100 % et 150 % du budget, passage automatique au modèle économique avec avis à la personne.
	setAI({ price_input_per_mtok: 1000, price_output_per_mtok: 1000, default_monthly_budget: 1000 });
	await reply("Bonjour, première question.");
	const spent = py("print(json.dumps(frappe.db.sql('select coalesce(sum(cost),0) from `tabCortex AI Usage`')[0][0]))");
	setAI({ default_monthly_budget: Math.max(spent / 1.2, 0.0001) }); // la dépense représente alors ~120 % du budget
	t = await reply("Bonjour, deuxième question.");
	check("S6 plafond atteint : avis « Plafond d'intelligence artificielle atteint » puis réponse", /Plafond d'intelligence artificielle atteint/.test(t) && /Je peux consulter/.test(t), t.slice(-220));
	setAI({ default_monthly_budget: Math.max(spent / 3, 0.0001) }); // au-delà de 150 % : refus clair
	t = await reply("Bonjour, troisième question.");
	check("S6 au-delà de 150 % : refus clair du budget", /budget mensuel/.test(t), t.slice(-160));
	setAI({ price_input_per_mtok: 0, price_output_per_mtok: 0, default_monthly_budget: 0 });
	py("frappe.db.sql(\"delete from `tabCortex AI Usage`\")\nprint(json.dumps(True))");

	// Sans clé : mode démonstration honnête, jamais de faux « modèle ».
	setAI({ api_key: "" });
	{
		const { ctx, page } = await session();
		const pill = (await page.locator("body").innerText());
		check("S7 sans clé : la page affiche « Démonstration »", /Démonstration/.test(pill));
		await ctx.close();
	}
} finally {
	setAI({ api_key: KEY, model: "gemini-3.8-flash", fallback_model: "", price_input_per_mtok: 0, price_output_per_mtok: 0, default_monthly_budget: 0 });
}

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} vérifications réussies`);
fs.writeFileSync(`${OUT}/resultats.json`, JSON.stringify(results, null, 1));
process.exit(failed.length ? 1 : 0);
