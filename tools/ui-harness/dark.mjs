import { chromium } from "playwright-core";
import http from "http"; import fs from "fs"; import path from "path";
const root = process.argv[2], outDir = process.argv[3];
const srv = http.createServer((q, r) => { const f = path.join(root, q.url.split("?")[0] === "/" ? "page.html" : q.url.split("?")[0]); if (!fs.existsSync(f)) { r.statusCode = 404; return r.end(); } r.setHeader("Content-Type", f.endsWith(".js") ? "text/javascript" : f.endsWith(".css") ? "text/css" : f.endsWith(".json") ? "application/json" : "text/html"); r.end(fs.readFileSync(f)); }).listen(0);
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
for (const theme of ["light", "dark"]) {
  const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
  await page.goto(`http://localhost:${srv.address().port}/`);
  await page.waitForSelector(".cp-stat");
  await page.evaluate((t) => { if (t === "dark") { document.documentElement.setAttribute("data-theme", "dark"); const l = document.createElement("link"); l.rel = "stylesheet"; l.href = "out/dark.css"; document.head.appendChild(l); document.body.style.background = "#111113"; document.body.style.color = "#f4f4f5"; } }, theme);
  await page.waitForTimeout(500);
  const result = await page.evaluate(() => {
    const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(",").map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
    const lum = ({ r, g, b }) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
    const bgOf = (el) => { while (el) { const c = parse(getComputedStyle(el).backgroundColor); if (c && c.a > 0.5) return c; el = el.parentElement; } return { r: 255, g: 255, b: 255 }; };
    const bad = []; let n = 0;
    document.querySelectorAll(".cp-action *, .cp-stat *").forEach((el) => {
      const own = [...el.childNodes].some((x) => x.nodeType === 3 && x.textContent.trim());
      if (!own) return;
      const cs = getComputedStyle(el); const isSvg = el instanceof SVGElement;
      const fg = parse(isSvg ? cs.fill : cs.color); if (!fg) return;
      const bg = bgOf(el); const a = lum(fg), b = lum(bg); const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      n++; if (ratio < 4.5) bad.push({ text: el.textContent.trim().slice(0, 30), ratio: Math.round(ratio * 100) / 100, cls: el.getAttribute("class") });
    });
    return { n, bad };
  });
  console.log(theme, "textes:", result.n, "sous 4,5:1:", JSON.stringify(result.bad));
  await page.screenshot({ path: `${outDir}/cartes-${theme}.png`, fullPage: true });
  await page.close();
}
await browser.close(); srv.close();
