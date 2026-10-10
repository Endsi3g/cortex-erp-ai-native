import { chromium } from "playwright-core";
import http from "http"; import fs from "fs"; import path from "path";
const root = process.argv[2];
const srv = http.createServer((q, r) => { const f = path.join(root, q.url.split("?")[0] === "/" ? "page.html" : q.url.split("?")[0]); if (!fs.existsSync(f)) { r.statusCode = 404; return r.end(); } r.setHeader("Content-Type", f.endsWith(".js") ? "text/javascript" : f.endsWith(".css") ? "text/css" : f.endsWith(".json") ? "application/json" : "text/html"); r.end(fs.readFileSync(f)); }).listen(0);
const port = srv.address().port;
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
const out = process.argv[3]; fs.mkdirSync(out, { recursive: true });
for (const [name, w] of [["bureau", 900], ["mobile", 390]]) {
  const page = await browser.newPage({ viewport: { width: w, height: 900 } });
  const errors = []; page.on("pageerror", e => errors.push(String(e))); page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(`http://localhost:${port}/`); await page.waitForSelector(".cp-stat", { timeout: 8000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${out}/cartes-${name}.png`, fullPage: true });
  if (name === "bureau") {
    // Interaction réelle : approuver le devis, puis ouvrir le lien du résultat; flèche d'une carte de stats.
    const card = page.locator(".cp-action").first();
    await card.getByRole("button", { name: "Créer le devis" }).click();
    await card.locator(".cp-action-badge", { hasText: "Fait" }).waitFor({ timeout: 4000 });
    console.log("etat apres approbation:", await card.locator(".cp-action-badge").innerText(), "|", await card.locator(".cp-action-foot").innerText());
    console.log("appel:", JSON.stringify(await page.evaluate(() => window.__calls.map(c => [c.method, c.args]))));
    await card.getByRole("button", { name: "Ouvrir le devis" }).click();
    await page.locator(".cp-stat-open").nth(1).click();
    console.log("routes:", JSON.stringify(await page.evaluate(() => window.__routes)));
    await page.screenshot({ path: `${out}/cartes-apres-approbation.png`, fullPage: true });
    // Refus d'une autre carte (échec réseau)
    await page.evaluate(() => { window.__fail = true; });
    const second = page.locator(".cp-action").nth(1);
    await second.getByRole("button", { name: "Créer le client" }).click();
    await page.waitForSelector(".cp-action-message", { timeout: 4000 });
    console.log("erreur affichee:", await second.locator(".cp-action-message").innerText(), "| bouton encore actif:", await second.getByRole("button", { name: "Créer le client" }).isEnabled());
  }
  console.log(name, "erreurs JS:", JSON.stringify(errors));
  await page.close();
}
await browser.close(); srv.close();
